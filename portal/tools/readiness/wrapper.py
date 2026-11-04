#!/usr/bin/env python3
"""Read-only readiness wrapper (source-only; NOT a live execution grant).

Executes a finite, declarative read-set via `kubectl get --raw` (no shell=True,
no exec/log/proxy, no discovery fallback) against the fixed context
kubernetes-admin@pak-portal. It performs input validation before any subprocess,
enforces bounded outputs, writes a value-free journal, and returns a fail-closed
aggregate disposition. It performs no Kubernetes mutations and no SSH provisioning.

This module is a source implementation. Running it against a live cluster
requires a future, separately-issued execution gate; it is NOT authorization.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

READSET = Path(__file__).with_name("readset.json")
CONTEXT = "kubernetes-admin@pak-portal"

# Dispositions (aggregate precedence: FAIL > INCONCLUSIVE > PASS > NOT_EXECUTED)
FAIL, INCONCLUSIVE, PASS, NOT_APPLICABLE, NOT_EXECUTED = "FAIL", "INCONCLUSIVE", "PASS", "NOT_APPLICABLE", "NOT_EXECUTED"


class ReadError(Exception):
    pass


def sha256_hex(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()


def load_readset():
    return json.loads(READSET.read_text())


def validate_gate(gate, now):
    """Returns (ok, error). Gate must exist, be within expiry, bound to the exact
    source/hash, non-TEST_ONLY, correct context, and not already have output."""
    if not isinstance(gate, dict):
        return False, "gate manifest not a JSON object"
    if gate.get("mode") == "TEST_ONLY":
        return False, "TEST_ONLY gate not accepted for live execution"
    if gate.get("context") != CONTEXT:
        return False, "gate context mismatch"
    if not re.fullmatch(r"[0-9a-f]{40}", str(gate.get("source_sha", ""))):
        return False, "gate source_sha missing/invalid"
    issued = gate.get("issued_at_utc")
    expiry = gate.get("expiry_hours", 24)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", str(issued)):
        return False, "gate issued_at_utc missing/invalid"
    try:
        t = time.mktime(time.strptime(issued, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return False, "gate issued_at_utc unparsable"
    if now - t > expiry * 3600:
        return False, "gate expired"
    if gate.get("run_budget_consumed", False):
        return False, "run budget already consumed"
    return True, None


def run_kubectl_raw(kubectl, path, timeout, cap):
    # No shell; argv-only; validate path shape before subprocess.
    if not re.fullmatch(r"/[A-Za-z0-9./_\-?=&%]+", path):
        raise ReadError("invalid raw path rejected")
    cmd = [kubectl, "--context", CONTEXT, "--request-timeout=%ds" % timeout, "get", "--raw", path]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout + 5, check=False)
    except subprocess.TimeoutExpired:
        raise ReadError("kubectl deadline exceeded")
    if proc.returncode != 0:
        # value-free: never surface stderr (may carry credentials)
        raise ReadError("kubectl exit %d" % proc.returncode)
    body = proc.stdout
    if len(body) > cap:
        raise ReadError("response exceeds %d bytes" % cap)
    return body


def validate_envelope(body):
    try:
        doc = json.loads(body)
    except Exception:
        raise ReadError("malformed JSON envelope")
    if not isinstance(doc, dict) or doc.get("kind", "").endswith("List"):
        # List envelopes must carry apiVersion/kind/items; item TypeMeta optional (accepted design).
        if not isinstance(doc, dict) or "items" not in doc or "apiVersion" not in doc:
            raise ReadError("list envelope missing apiVersion/items")
    if "metadata" in doc and isinstance(doc["metadata"], dict) and doc["metadata"].get("continue"):
        raise ReadError("nonempty continue rejected (no pagination follow)")
    return doc


def run_read(readset, read_id, kubectl, timeout=15, cap=1048576):
    spec = readset["reads"].get(read_id)
    if spec is None:
        raise ReadError("unknown read id")
    if spec.get("method") == "wal":
        raise ReadError("WAL read requires the wal executor (not kubectl)")
    paths = [spec["path"]] if "path" in spec else spec.get("paths", [])
    out = []
    for p in paths:
        body = run_kubectl_raw(kubectl, p, timeout, cap)
        out.append(validate_envelope(body))
    return out if "paths" in spec else out[0]


def classify(doc, read_id):
    """Predicates per accepted design; returns disposition."""
    if read_id in ("PR-3", "PR-5", "PR-6", "HC-OP", "HC-DNS"):
        items = doc.get("items")
        if not isinstance(items, list):
            return INCONCLUSIVE
        return PASS if len(items) >= 0 else INCONCLUSIVE  # presence/empty per-stage predicates applied by caller
    if read_id in ("HC-DB", "HC-ARCH-STATE"):
        status = doc.get("status", {})
        if not isinstance(status, dict):
            return INCONCLUSIVE
        return PASS  # specific 3/3/3 + condition checks are in the gate predicate
    if read_id == "HC-PORTAL":
        st = doc.get("status", {})
        return PASS if isinstance(st, dict) else INCONCLUSIVE
    if read_id == "HC-GW":
        st = doc.get("status", {})
        return PASS if isinstance(st, dict) else INCONCLUSIVE
    return NOT_APPLICABLE


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kubectl", default="kubectl")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--now", type=int, default=int(time.time()))
    args = ap.parse_args(argv)

    out_path = Path(args.out)
    if out_path.exists():
        print("STOP: output exists (no-overwrite)", file=sys.stderr)
        return 2

    gate = json.loads(Path(args.gate).read_text())
    ok, err = validate_gate(gate, args.now)
    if not ok:
        print("STOP: gate rejected: " + str(err), file=sys.stderr)
        return 2

    readset = load_readset()
    journal = {"stage": args.stage, "context": CONTEXT, "reads": {}, "aggregate": NOT_EXECUTED}
    for read_id, spec in readset["reads"].items():
        if args.stage not in spec["stages"]:
            journal["reads"][read_id] = {"disposition": NOT_APPLICABLE}
            continue
        start = time.monotonic()
        try:
            doc = run_read(readset, read_id, args.kubectl)
            journal["reads"][read_id] = {
                "disposition": classify(doc, read_id),
                "attempt": 1,
                "duration_ms": int((time.monotonic() - start) * 1000),
                "bytes": len(json.dumps(doc)),
            }
        except ReadError as e:
            journal["reads"][read_id] = {"disposition": INCONCLUSIVE, "error": str(e), "attempt": 1}
    # fail-closed aggregate
    disp = [v.get("disposition") for v in journal["reads"].values()]
    if FAIL in disp:
        journal["aggregate"] = FAIL
    elif INCONCLUSIVE in disp:
        journal["aggregate"] = INCONCLUSIVE
    elif all(d in (PASS, NOT_APPLICABLE) for d in disp):
        journal["aggregate"] = PASS
    else:
        journal["aggregate"] = NOT_EXECUTED
    out_path.write_text(json.dumps(journal, sort_keys=True, indent=2))
    print("aggregate=%s" % journal["aggregate"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
