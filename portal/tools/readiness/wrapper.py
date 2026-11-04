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
import select
import subprocess
import sys
import time
from pathlib import Path

import wal  # noqa: E402  (same-directory WAL observation module)

READSET = Path(__file__).with_name("readset.json")
CONTEXT = "kubernetes-admin@pak-portal"
FAIL, INCONCLUSIVE, PASS, NOT_APPLICABLE = "FAIL", "INCONCLUSIVE", "PASS", "NOT_APPLICABLE"
STAGES = ["S0", "S1", "S2a", "S2b", "S3", "S4"]


class ReadError(Exception):
    pass


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def package_hash():
    return sha256_hex(READSET.read_bytes() + Path(__file__).read_bytes() + Path(__file__).with_name("wal.py").read_bytes())


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
    hard_deadline = time.monotonic() + timeout + 5
    chunks = []
    total = 0
    fd = proc.stdout.fileno()
    try:
        while True:
            remain = hard_deadline - time.monotonic()
            if remain <= 0:
                raise ReadError("kubectl deadline exceeded")
            r, _, _ = select.select([fd], [], [], max(0.0, remain))
            if fd not in r:
                if proc.poll() is not None:
                    break
                continue
            buf = os.read(fd, min(65536, cap - total + 1))
            if not buf:
                break
            total += len(buf)
            if total > cap:
                raise ReadError("response exceeds %d bytes" % cap)
            chunks.append(buf)
    finally:
        try:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
        except Exception:
            pass
        try:
            proc.stderr.close()
        except Exception:
            pass
    if proc.returncode != 0:
        raise ReadError("kubectl exit %d" % proc.returncode)
    return b"".join(chunks), proc.returncode


def validate_envelope(body, expect_list):
    try:
        doc = json.loads(body)
    except Exception:
        raise ReadError("malformed JSON")
    if not isinstance(doc, dict):
        raise ReadError("envelope not object")
    api = doc.get("apiVersion", "")
    kind = doc.get("kind", "")
    allowed_api_prefix = ("v1", "apps/v1", "networking.k8s.io/v1", "discovery.k8s.io/v1",
                          "projectcalico.org/v3", "crd.projectcalico.org/v1",
                          "postgresql.cnpg.io/v1", "gateway.networking.k8s.io/v1")
    if not isinstance(api, str) or not api.startswith(allowed_api_prefix):
        raise ReadError("unexpected apiVersion")
    if isinstance(kind, str) and ("Secret" in kind or "ConfigMap" in kind):
        raise ReadError("forbidden list kind")
    if expect_list:
        if not isinstance(kind, str) or not kind.endswith("List"):
            raise ReadError("expected List envelope")
        meta = doc.get("metadata")
        if not isinstance(meta, dict) or meta.get("continue") is not None:
            raise ReadError("invalid/absent metadata.continue")
        if not isinstance(doc.get("items"), list):
            raise ReadError("items not list")
        return doc
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
        for port in it.get("ports", []):
            if port.get("port") != 6443 or port.get("protocol") != "TCP":
                return FAIL, "unexpected API port/protocol"
        for ep in it.get("endpoints", []):
            if ep.get("conditions", {}).get("ready") is not True:
                return FAIL, "unready API endpoint"
            for a in ep.get("addresses", []):
                addrs.add(a)
    want = {"172.30.140.101", "172.30.140.102", "172.30.140.103"}
    if addrs == want:
        return PASS, "exact ready API tuples"
    if want < addrs:
        return FAIL, "extra API addresses"
    return INCONCLUSIVE, "missing/partial API tuples"


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
    # nine responses; policy lists AND Tier/Felix must be empty (baseline). ns/pods presence checked only.
    if not isinstance(docs, list) or len(docs) != 9:
        return FAIL, "expected 9 responses"
    for name, idx in (("KNP", 0), ("NP", 1), ("GNP", 2), ("HEP", 3), ("CNP", 4), ("Tier", 5), ("Felix", 6)):
        if docs[idx].get("items"):
            return FAIL, "%s nonempty (baseline drift)" % name
    return PASS, "policy/tier/felix baseline empty"


def pred_hc_op(doc):
    pods = doc.get("items", [])
    if not pods:
        return INCONCLUSIVE, "operator pods empty"
    for p in pods:
        if p.get("metadata", {}).get("deletionTimestamp"):
            return FAIL, "operator pod terminating"
        conds = {c.get("type"): c for c in p.get("status", {}).get("conditions", []) if isinstance(c, dict)}
        if conds.get("Ready", {}).get("status") != "True":
            return FAIL, "operator pod not Ready"
    return PASS, "operator ready"


def pred_hc_dns(doc):
    ready = False
    for it in doc.get("items", []):
        for ep in it.get("endpoints", []):
            if ep.get("conditions", {}).get("ready") is True:
                if not ep.get("addresses"):
                    return FAIL, "DNS ready endpoint without address"
                ready = True
    if not ready:
        return INCONCLUSIVE, "no ready DNS endpoints"
    ports = set()
    for it in doc.get("items", []):
        for port in it.get("ports", []):
            ports.add((port.get("port"), port.get("protocol")))
    if (53, "TCP") in ports and (53, "UDP") in ports:
        return PASS, "DNS ready with 53/TCP+UDP"
    return INCONCLUSIVE, "DNS ports incomplete"


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

# ---- WAL executor (ER-04) ----

def default_http_get(url, timeout, cap):
    # No redirects, NO environment proxy; used only in an authorized live session.
    import urllib.request
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            raise ReadError("redirect forbidden")
    opener = urllib.request.build_opener(NoRedirect, urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url)
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(cap + 1)
            if len(body) > cap:
                raise ReadError("metrics response exceeds cap")
            return body
    except ReadError:
        raise
    except Exception as e:
        raise ReadError("metrics fetch failed: %s" % type(e).__name__)


def run_wal_sample(kubectl, http_get, clock_evidence, gate):
    """5-request sample: Cluster -> Pod -> metrics -> same Pod -> same Cluster."""
    def raw(path):
        body, _ = run_kubectl_raw(kubectl, path, 5, 256 * 1024)
        return validate_envelope(body, False)

    cluster_path = "/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db"
    cluster = raw(cluster_path)
    primary = cluster.get("status", {}).get("currentPrimary")
    if not primary:
        return INCONCLUSIVE, "no currentPrimary"
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", str(primary)):
        return INCONCLUSIVE, "invalid primary name"
    pod_path = "/api/v1/namespaces/portal/pods/" + str(primary)
    pod = raw(pod_path)
    pod_ip = pod.get("status", {}).get("podIP")
    if not pod_ip:
        return INCONCLUSIVE, "pod IP missing"
    try:
        metrics_text = http_get("http://%s:9187/metrics" % pod_ip, wal.REQ_TIMEOUT, wal.METRIC_CAP).decode()
    except ReadError as e:
        return INCONCLUSIVE, str(e)
    pod_after = raw(pod_path)
    cluster_after = raw(cluster_path)
    disp, m, detail = wal.wal_sample(cluster, pod, metrics_text, cluster_after, pod_after,
                                     clock_evidence, baseline=gate.get("wal_baseline"),
                                     op_end_utc=gate.get("operation_end_utc"))
    return disp, detail


STAGE_ORDER = ["S0", "S1", "S2a", "S2b", "S3", "S4"]


def next_stage(last):
    if last is None or last == "":
        return "S0"
    if last not in STAGE_ORDER:
        return None
    idx = STAGE_ORDER.index(last)
    return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--kubectl", default="kubectl")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--now", type=int, default=None, help="ignored (test-only clock injection uses time.time patch)")
    args = ap.parse_args(argv)

    now = int(time.time())  # expiry always uses the real/patched clock; --now never bypasses it
    _ = args.now
    gate = json.loads(Path(args.gate).read_text())
    ok, err = validate_gate(gate, now)
    if not ok:
        print("STOP: gate rejected: %s" % err, file=sys.stderr)
        return 2
    if args.stage not in STAGES:
        print("STOP: unknown stage", file=sys.stderr)
        return 2
    os.makedirs(args.state_dir, exist_ok=True)
    # stage ordering: only the successor of the last completed stage may run
    receipt_path = os.path.join(args.state_dir, "stage.receipt")
    last = open(receipt_path).read().strip() if os.path.exists(receipt_path) else None
    if args.stage != next_stage(last):
        print("STOP: stage out of order (expected %s)" % next_stage(last), file=sys.stderr)
        return 2
    # run reservation keyed by package identity + stage, at a location stable across --state-dir
    base = os.path.dirname(os.path.abspath(args.state_dir))
    reserve_path = os.path.join(base, "p8c-%s-%s.reserved" % (gate.get("package_sha256", "")[:16], args.stage))
    if atomic_reserve(reserve_path) is None:
        print("STOP: run/stage already reserved (replay blocked)", file=sys.stderr)
        return 2
    # output no-overwrite: pre-existing evidence is preserved
    out = Path(args.out)
    if out.exists():
        print("STOP: output already exists", file=sys.stderr)
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
                disp, detail = run_wal_sample(args.kubectl, default_http_get, gate.get("clock_evidence"), gate)
                journal["reads"][read_id] = {"disposition": disp, "detail": detail,
                                             "attempt": 1, "duration_ms": int((time.monotonic() - start) * 1000)}
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
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(journal, sort_keys=True, indent=2))
    os.chmod(tmp, 0o600)
    os.replace(tmp, out)  # out does not exist (checked above); atomic publish
    with open(receipt_path, "w") as f:
        f.write(args.stage)
    print("aggregate=%s" % agg)
    return 0 if agg == PASS else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
