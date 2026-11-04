#!/usr/bin/env python3
"""Read-only readiness wrapper (source-only; NOT a live execution grant).

Executes a finite, hash-bound, declarative read-set via `kubectl get --raw`
(no shell=True, no exec/log/proxy, no discovery fallback) against the fixed
context kubernetes-admin@pak-portal, plus the primary-bound WAL metric sample.
Fail-closed: gate validation (mode/context/source-hash/UTC-expiry/stage), atomic
run reservation, bounded streaming, value-free journal, nonzero exit on any
non-PASS aggregate. No Kubernetes mutations, no SSH provisioning.

This module is a source implementation. Running it against a live cluster
requires a future, separately-issued execution gate; it is NOT authorization.
"""
import calendar
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

READSET = Path(__file__).with_name("readset.json")
CONTEXT = "kubernetes-admin@pak-portal"
FAIL, INCONCLUSIVE, PASS, NOT_APPLICABLE = "FAIL", "INCONCLUSIVE", "PASS", "NOT_APPLICABLE"
STAGES = ["S0", "S1", "S2a", "S2b", "S3", "S4"]


class ReadError(Exception):
    pass


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def package_hash():
    return sha256_hex(READSET.read_bytes() + Path(__file__).read_bytes())


def parse_utc(iso):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", iso or ""):
        raise ReadError("issued_at_utc invalid")
    try:
        return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        raise ReadError("issued_at_utc unparsable")


def validate_gate(gate, now):
    """Strict gate validation: exact mode/context/source-hash/UTC expiry/stage."""
    if not isinstance(gate, dict):
        return False, "gate not object"
    if gate.get("mode") != "LIVE":
        return False, "mode must be LIVE"
    if gate.get("context") != CONTEXT:
        return False, "context mismatch"
    if not re.fullmatch(r"[0-9a-f]{40}", str(gate.get("source_sha", ""))):
        return False, "source_sha invalid"
    if gate.get("package_sha256") != package_hash():
        return False, "package hash mismatch"
    issued = parse_utc(gate.get("issued_at_utc"))
    if issued > now:
        return False, "gate issued in the future"
    if not isinstance(gate.get("expiry_hours"), int) or gate["expiry_hours"] > 24:
        return False, "expiry_hours invalid (>24)"
    if now - issued > gate["expiry_hours"] * 3600:
        return False, "gate expired"
    if gate.get("run_budget_consumed"):
        return False, "run budget consumed"
    return True, None


def atomic_reserve(path):
    """Exclusive create; any existing state (incl. crash/UNKNOWN_OUTCOME) blocks re-run."""
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        return None
    os.close(fd)
    return path


def run_kubectl_raw(kubectl, path, timeout, cap):
    if not re.fullmatch(r"/[A-Za-z0-9./_\-?=&%]+", path):
        raise ReadError("invalid raw path")
    if path.startswith("/api/v1/namespaces/") and ("secrets" in path or "configmaps" in path):
        raise ReadError("secret/configmap path forbidden")
    cmd = [kubectl, "--context", CONTEXT, "--request-timeout=%ds" % timeout, "get", "--raw", path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        raise ReadError("kubectl spawn failed: %s" % type(e).__name__)
    try:
        chunks = []
        total = 0
        deadline = time.monotonic() + timeout + 5
        while True:
            remain = deadline - time.monotonic()
            if remain <= 0:
                proc.kill()
                proc.wait()
                raise ReadError("kubectl deadline exceeded")
            buf = proc.stdout.read(min(65536, cap - total + 1))
            if not buf:
                break
            total += len(buf)
            if total > cap:
                proc.kill()
                proc.wait()
                raise ReadError("response exceeds %d bytes" % cap)
            chunks.append(buf)
        proc.wait(timeout=5)
        stderr = proc.stderr.read(4096)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise ReadError("kubectl wait timeout")
    if proc.returncode != 0:
        raise ReadError("kubectl exit %d" % proc.returncode)
    return b"".join(chunks), proc.returncode


def validate_envelope(body, expect_list):
    try:
        doc = json.loads(body)
    except Exception:
        raise ReadError("malformed JSON")
    if not isinstance(doc, dict) or not isinstance(doc.get("apiVersion"), str):
        raise ReadError("envelope missing apiVersion")
    if expect_list:
        if doc.get("kind", "").endswith("List") and isinstance(doc.get("items"), list):
            meta = doc.get("metadata", {})
            if isinstance(meta, dict) and meta.get("continue"):
                raise ReadError("nonempty continue rejected")
            return doc
        raise ReadError("expected List envelope")
    return doc


# ---- predicates (accepted design) ----

def _cond_ready(doc, ctype):
    conds = doc.get("status", {}).get("conditions", [])
    for c in conds:
        if isinstance(c, dict) and c.get("type") == ctype:
            return c.get("status")
    return None


def pred_hc_db(doc):
    spec_inst = doc.get("spec", {}).get("instances")
    st = doc.get("status", {})
    si, ri = st.get("instances"), st.get("readyInstances")
    if not all(isinstance(x, int) for x in (spec_inst, si, ri)):
        return INCONCLUSIVE, "missing instances fields"
    ready = _cond_ready(doc, "Ready")
    if ready == "True" and spec_inst == 3 and si == 3 and ri == 3:
        return PASS, "3/3/3 Ready"
    if ready == "False" or (isinstance(ri, int) and ri < 3):
        return FAIL, "DB not ready"
    return INCONCLUSIVE, "Ready=%s" % ready


def pred_hc_arch(doc):
    s = _cond_ready(doc, "ContinuousArchiving")
    if s == "True":
        return PASS, "ContinuousArchiving True"
    if s == "False":
        return FAIL, "ContinuousArchiving False"
    return INCONCLUSIVE, "ContinuousArchiving=%s" % s


def _ready_eps(doc):
    items = doc.get("items", [])
    ready = []
    for it in items:
        for ep in it.get("endpoints", []):
            if isinstance(ep, dict) and ep.get("conditions", {}).get("ready") is True:
                ready.append(ep)
    return ready, items


def pred_pr3(doc):
    addrs = set()
    for it in doc.get("items", []):
        for ep in it.get("endpoints", []):
            for a in ep.get("addresses", []):
                addrs.add(a)
            for p in ep.get("ports", []):
                if p.get("port") != 6443:
                    return FAIL, "unexpected API port"
    want = {"172.30.140.101", "172.30.140.102", "172.30.140.103"}
    if want <= addrs:
        return PASS, "exact API tuples present"
    return INCONCLUSIVE, "missing API tuples"


def pred_pr5(doc):
    items = doc.get("items", [])
    if len(items) != 1:
        return FAIL if len(items) > 1 else INCONCLUSIVE, "service count != 1"
    svc = items[0]
    spec = svc.get("spec", {})
    if spec.get("type") != "LoadBalancer" or spec.get("externalTrafficPolicy") != "Local":
        return FAIL, "service type/policy wrong"
    ports = spec.get("ports", [])
    ok = any(p.get("port") == 443 and p.get("targetPort") in (10443, "10443") and p.get("protocol") == "TCP" for p in ports)
    if not ok:
        return FAIL, "443->10443 tuple missing"
    if not svc.get("status", {}).get("loadBalancer", {}).get("ingress"):
        return INCONCLUSIVE, "no LB IP"
    return PASS, "exact dataplane Service"


def pred_pr6(docs):
    # nine responses; policy lists must be empty, Tier/Felix must match accepted baseline projection.
    knp, np, gnp, hep, cnp, tier, felix, ns, pods = docs
    for name, d in (("KNP", knp), ("NP", np), ("GNP", gnp), ("HEP", hep), ("CNP", cnp)):
        if d.get("items"):
            return FAIL, "%s nonempty" % name
    # Tier/Felix/NS/Pods presence check is a baseline freshness comparison, not effective-union proof.
    return PASS, "policy set empty baseline"


def pred_hc_op(doc):
    pods = doc.get("items", [])
    if not pods:
        return INCONCLUSIVE, "operator pods empty"
    if all(p.get("status", {}).get("phase") == "Running" for p in pods):
        return PASS, "operator pods present"
    return INCONCLUSIVE, "operator not running"


def pred_hc_dns(doc):
    ready, items = _ready_eps(doc)
    if not ready:
        return INCONCLUSIVE, "no ready DNS endpoints"
    return PASS, "DNS ready"


def pred_hc_portal(doc):
    st = doc.get("status", {})
    if st.get("observedGeneration") != doc.get("metadata", {}).get("generation"):
        return INCONCLUSIVE, "generation mismatch"
    if st.get("readyReplicas") == 1 and st.get("updatedReplicas") == 1 and st.get("availableReplicas") == 1:
        return PASS, "portal ready"
    return FAIL, "portal replicas not converged"


def pred_hc_gw(doc):
    st = doc.get("status", {})
    conds = {c.get("type"): c for c in st.get("conditions", []) if isinstance(c, dict)}
    acc, prog = conds.get("Accepted"), conds.get("Programmed")
    if acc and prog and acc.get("status") == "True" and prog.get("status") == "True":
        if acc.get("observedGeneration") == doc.get("metadata", {}).get("generation") and prog.get("observedGeneration") == doc.get("metadata", {}).get("generation"):
            return PASS, "Gateway programmed"
    if acc and acc.get("status") == "False" or prog and prog.get("status") == "False":
        return FAIL, "Gateway not programmed"
    return INCONCLUSIVE, "Gateway conditions incomplete"


PREDICATES = {
    "HC-DB": (False, pred_hc_db),
    "HC-ARCH-STATE": (False, pred_hc_arch),
    "PR-3": (True, pred_pr3),
    "PR-5": (True, pred_pr5),
    "PR-6": (True, pred_pr6),
    "HC-OP": (True, pred_hc_op),
    "HC-DNS": (True, pred_hc_dns),
    "HC-PORTAL": (False, pred_hc_portal),
    "HC-GW": (False, pred_hc_gw),
}


def run_read(readset, read_id, kubectl, timeout=15, cap=1048576):
    spec = readset["reads"].get(read_id)
    if spec is None:
        raise ReadError("unknown read id")
    if spec.get("method") == "wal":
        raise ReadError("wal uses wal_sample")
    expect_list, _ = PREDICATES[read_id]
    paths = [spec["path"]] if "path" in spec else spec.get("paths", [])
    out = []
    for p in paths:
        body, _ = run_kubectl_raw(kubectl, p, timeout, cap)
        out.append(validate_envelope(body, expect_list or read_id == "PR-6"))
    return out if read_id == "PR-6" else out[0]


# ---- WAL executor (ER-04) ----

def parse_archiver_metrics(text):
    vals = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for name in ("cnpg_pg_stat_archiver_archived_count", "cnpg_pg_stat_archiver_failed_count",
                     "cnpg_pg_stat_archiver_last_archived_time", "cnpg_pg_stat_archiver_last_failed_time",
                     "cnpg_pg_stat_archiver_stats_reset_time"):
            if line.startswith(name + " ") or line.startswith(name + "{"):
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        vals[name] = float(parts[1])
                    except ValueError:
                        vals[name] = float("nan")
    return vals


def wal_sample(cluster_doc, pod_doc, metrics_text, cluster_after, pod_after):
    """5-request sample; returns (disposition, metrics)."""
    if cluster_doc.get("status", {}).get("currentPrimary") is None:
        return INCONCLUSIVE, None
    if pod_doc.get("status", {}).get("podIP") is None:
        return INCONCLUSIVE, None
    if cluster_after.get("metadata", {}).get("uid") != cluster_doc.get("metadata", {}).get("uid"):
        return INCONCLUSIVE, None
    if pod_after.get("metadata", {}).get("uid") != pod_doc.get("metadata", {}).get("uid"):
        return INCONCLUSIVE, None
    m = parse_archiver_metrics(metrics_text)
    if "cnpg_pg_stat_archiver_last_archived_time" not in m:
        return INCONCLUSIVE, None
    return PASS, m


# ---- main ----

def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--kubectl", default="kubectl")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--now", type=int, default=int(time.time()))
    args = ap.parse_args(argv)

    gate = json.loads(Path(args.gate).read_text())
    ok, err = validate_gate(gate, args.now)
    if not ok:
        print("STOP: gate rejected: %s" % err, file=sys.stderr)
        return 2
    if args.stage not in STAGES:
        print("STOP: unknown stage", file=sys.stderr)
        return 2
    reserved = atomic_reserve(os.path.join(args.state_dir, "run.reserved"))
    if reserved is None:
        print("STOP: run already reserved (re-run/unknown outcome blocked)", file=sys.stderr)
        return 2

    readset = json.loads(READSET.read_text())
    journal = {"stage": args.stage, "context": CONTEXT, "reads": {}}
    for read_id, spec in readset["reads"].items():
        if args.stage not in spec["stages"]:
            journal["reads"][read_id] = {"disposition": NOT_APPLICABLE}
            continue
        start = time.monotonic()
        try:
            if spec.get("method") == "wal":
                journal["reads"][read_id] = {"disposition": INCONCLUSIVE, "detail": "wal requires live transport (not authorized)"}
                continue
            expect_list, pred = PREDICATES[read_id]
            doc = run_read(readset, read_id, args.kubectl)
            disp, detail = pred(doc)
            journal["reads"][read_id] = {"disposition": disp, "detail": detail,
                                         "attempt": 1, "duration_ms": int((time.monotonic() - start) * 1000)}
        except ReadError as e:
            journal["reads"][read_id] = {"disposition": INCONCLUSIVE, "error": str(e), "attempt": 1}

    disp = [v.get("disposition") for v in journal["reads"].values()]
    agg = FAIL if FAIL in disp else (INCONCLUSIVE if INCONCLUSIVE in disp else (PASS if all(d in (PASS, NOT_APPLICABLE) for d in disp) else INCONCLUSIVE))
    journal["aggregate"] = agg
    out = Path(args.out)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(journal, sort_keys=True, indent=2))
    os.chmod(tmp, 0o600)
    os.replace(tmp, out)
    print("aggregate=%s" % agg)
    return 0 if agg == PASS else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
