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
import tempfile
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


RESERVATION_BASE = os.path.join(tempfile.gettempdir(), "p8c-readiness")

_TRANSPORT = {"requests": 0, "bytes": 0}


def _reset_transport():
    global _TRANSPORT
    _TRANSPORT = {"requests": 0, "bytes": 0}


def _count_transport(nbytes):
    global _TRANSPORT
    _TRANSPORT["requests"] += 1
    _TRANSPORT["bytes"] += int(nbytes)


def budget_path(gate):
    """Budget is keyed by stable package identity (not state/output path)."""
    return os.path.join(RESERVATION_BASE, str(gate.get("package_sha256", ""))[:32], "budget.json")


def budget_exhausted(budget):
    return (budget.get("requests", 0) >= 90 or budget.get("bytes", 0) >= 36 * 1024 * 1024
            or budget.get("seconds", 0.0) >= 3960)


def reservation_path(gate, stage):
    """Stable one-run authority location: keyed by package identity, NOT state/output path."""
    return os.path.join(RESERVATION_BASE, str(gate.get("package_sha256", ""))[:32], stage + ".window.json")


def read_window_state(path):
    if not os.path.exists(path):
        return None
    try:
        return json.loads(open(path).read())
    except Exception:
        return None


def write_window_state(path, st):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def open_window(gate, stage):
    """Acquire or retry a stage window. A clean non-PASS allows retry (<=3 slots);
    an inflight (crashed) or completed window is blocked (no retry/replay)."""
    path = reservation_path(gate, stage)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    st = read_window_state(path)
    if st is not None:
        if not isinstance(st, dict) or st.get("source_sha") != gate.get("source_sha"):
            return "blocked", "window state unbound/corrupt"
        status = st.get("status", "inflight")
        if status == "completed":
            return "blocked", "stage already completed (no replay)"
        if status == "inflight":
            return "blocked", "window inflight (crash/UNKNOWN_OUTCOME; no retry)"
        if status != "clean_failed":
            return "blocked", "window state invalid"
        if st.get("attempts", 0) >= 3:
            return "blocked", "stage slots exhausted (no retry)"
        st["attempts"] = st.get("attempts", 0) + 1
        st["status"] = "inflight"
        write_window_state(path, st)
        return "retry", st
    # first attempt: exclusive create
    st = {"stage": stage, "source_sha": gate.get("source_sha"),
          "package_sha256": gate.get("package_sha256"), "attempts": 1,
          "status": "inflight", "completed": False}
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except FileExistsError:
        return "blocked", "window already opened (race)"
    write_window_state(path, st)
    return "first", st


def fail_window(gate, stage):
    path = reservation_path(gate, stage)
    st = read_window_state(path) or {}
    st["status"] = "clean_failed"
    write_window_state(path, st)


def complete_window(gate, stage):
    path = reservation_path(gate, stage)
    st = read_window_state(path) or {}
    st["status"] = "completed"
    st["completed"] = True
    write_window_state(path, st)


def read_receipt(receipt_path, gate):
    """Read the last VERIFIED completed stage; unbound/plain-text/invalid receipts are not authority."""
    if not os.path.exists(receipt_path):
        return None
    try:
        r = json.loads(open(receipt_path).read())
    except Exception:
        return None
    if not isinstance(r, dict):
        return None
    if r.get("source_sha") != gate.get("source_sha") or r.get("package_sha256") != gate.get("package_sha256"):
        return None
    if r.get("aggregate") != "PASS" or r.get("stage") not in STAGE_ORDER:
        return None
    return r["stage"]


def write_receipt(receipt_path, gate, stage):
    receipt = {"source_sha": gate.get("source_sha"), "package_sha256": gate.get("package_sha256"),
               "issued_at_utc": gate.get("issued_at_utc"), "stage": stage, "aggregate": "PASS"}
    tmp = receipt_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(receipt, f, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, receipt_path)


def write_failure_state(state_dir, gate, stage, agg):
    """Persist a bound non-PASS outcome (NOT a PASS receipt). Allowance stays consumed."""
    marker = {"source_sha": gate.get("source_sha"), "package_sha256": gate.get("package_sha256"),
              "issued_at_utc": gate.get("issued_at_utc"), "stage": stage, "aggregate": agg}
    p = os.path.join(state_dir, stage + ".failed.json")
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(marker, f, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def read_budget(state_dir):
    p = os.path.join(state_dir, "budget.json")
    if not os.path.exists(p):
        return {"requests": 0, "bytes": 0, "seconds": 0.0}
    try:
        return json.loads(open(p).read())
    except Exception:
        raise ReadError("budget state corrupt")


def write_budget(state_dir, budget):
    p = os.path.join(state_dir, "budget.json")
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(budget, f, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def persist_wal_baseline(state_dir, gate, metrics):
    """Persist the latest WAL archive metrics as the baseline for the next stage's sample."""
    p = os.path.join(state_dir, "wal-baseline.json")
    rec = {"source_sha": gate.get("source_sha"), "package_sha256": gate.get("package_sha256"),
           "issued_at_utc": gate.get("issued_at_utc"), "metrics": metrics}
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def read_wal_baseline(state_dir, gate):
    p = os.path.join(state_dir, "wal-baseline.json")
    if not os.path.exists(p):
        return None
    try:
        rec = json.loads(open(p).read())
    except Exception:
        return None
    if rec.get("source_sha") == gate.get("source_sha") and rec.get("package_sha256") == gate.get("package_sha256"):
        return rec.get("metrics")
    return None


def read_slot_count(state_dir, stage):
    p = os.path.join(state_dir, stage + ".slots.json")
    if not os.path.exists(p):
        return 0
    try:
        return int(json.loads(open(p).read()).get("attempted", 0))
    except Exception:
        return 0


def increment_slot(state_dir, stage):
    n = read_slot_count(state_dir, stage) + 1
    p = os.path.join(state_dir, stage + ".slots.json")
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"attempted": n}, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)
    return n


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
    eof = False
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
                eof = True
                break  # stdout EOF is NOT child failure; wait for the child to exit
            total += len(buf)
            if total > cap:
                raise ReadError("response exceeds %d bytes" % cap)
            chunks.append(buf)
        # after EOF (or process exit), wait for the child to finish within the remaining deadline
        if eof:
            try:
                proc.wait(timeout=max(0.1, hard_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise ReadError("kubectl did not exit after stdout EOF")
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


ALLOWED_API = ("v1", "apps/v1", "networking.k8s.io/v1", "discovery.k8s.io/v1",
               "projectcalico.org/v3", "crd.projectcalico.org/v1",
               "postgresql.cnpg.io/v1", "gateway.networking.k8s.io/v1",
               "policy.networking.k8s.io/v1alpha2")


def validate_envelope(body, expect_list):
    try:
        doc = json.loads(body)
    except Exception:
        raise ReadError("malformed JSON")
    if not isinstance(doc, dict):
        raise ReadError("envelope not object")
    api = doc.get("apiVersion", "")
    kind = doc.get("kind", "")
    if not isinstance(api, str) or api not in ALLOWED_API:
        raise ReadError("unexpected apiVersion")
    if isinstance(kind, str) and ("Secret" in kind or "ConfigMap" in kind):
        raise ReadError("forbidden list kind")
    if expect_list:
        if not isinstance(kind, str) or not kind.endswith("List"):
            raise ReadError("expected List envelope")
        meta = doc.get("metadata")
        if not isinstance(meta, dict):
            raise ReadError("metadata missing")
        if "continue" in meta:
            cont = meta["continue"]
            if cont is None:
                raise ReadError("null continue rejected")
            if not isinstance(cont, str) or cont != "":
                raise ReadError("nonempty continue rejected")
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
    saw_ready = False
    for it in doc.get("items", []):
        item_addrs = set()
        item_has_port = False
        for port in it.get("ports", []):
            if port.get("port") == 6443 and port.get("protocol") == "TCP":
                item_has_port = True
            else:
                return FAIL, "unexpected API port/protocol"
        for ep in it.get("endpoints", []):
            if ep.get("conditions", {}).get("ready") is not True:
                return FAIL, "unready API endpoint"
            for a in ep.get("addresses", []):
                item_addrs.add(a)
        if item_addrs and not item_has_port:
            return FAIL, "API addresses without port in same slice"
        if item_has_port and not item_addrs:
            return FAIL, "API port without addresses in same slice"
        addrs |= item_addrs
        if item_addrs:
            saw_ready = True
    if not saw_ready:
        return INCONCLUSIVE, "no API endpoints"
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
    # nine responses: policy lists empty; Tier/Felix compared to accepted safe baseline projection.
    if not isinstance(docs, list) or len(docs) != 9:
        return FAIL, "expected 9 responses"
    for name, idx in (("KNP", 0), ("NP", 1), ("GNP", 2), ("HEP", 3), ("CNP", 4)):
        if docs[idx].get("items"):
            return FAIL, "%s nonempty" % name
    # Tier baseline (accepted inventory): exactly default/Deny, kube-admin/Pass, kube-baseline/Pass
    tiers = docs[5].get("items", [])
    tier_sig = set()
    for t in tiers:
        m = t.get("metadata", {}) if isinstance(t, dict) else {}
        s = t.get("spec", {}) if isinstance(t, dict) else {}
        tier_sig.add((m.get("name"), s.get("order"), s.get("defaultAction")))
    expected_tier = {("default", 1000000, "Deny"), ("kube-admin", 1000, "Pass"), ("kube-baseline", 10000000, "Pass")}
    if tier_sig != expected_tier:
        return FAIL, "tier baseline drift"
    # Felix baseline (accepted): default with nftablesMode=Auto, all other fields null/absent
    felix = docs[6].get("items", [])
    if len(felix) != 1 or not isinstance(felix[0], dict):
        return FAIL, "felix baseline missing"
    f = felix[0]
    if f.get("metadata", {}).get("name") != "default":
        return FAIL, "felix name drift"
    fspec = f.get("spec", {}) if isinstance(f.get("spec"), dict) else {}
    for k, v in fspec.items():
        if k == "nftablesMode":
            if v != "Auto":
                return FAIL, "felix nftablesMode drift"
        elif v is not None:
            return FAIL, "felix field drift: " + k
    return PASS, "policy empty + tier/felix match accepted baseline"


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
    for it in doc.get("items", []):
        ports = {(p.get("port"), p.get("protocol")) for p in it.get("ports", [])}
        has_53 = (53, "TCP") in ports and (53, "UDP") in ports
        ready = False
        for ep in it.get("endpoints", []):
            if ep.get("conditions", {}).get("ready") is True:
                if not ep.get("addresses"):
                    return FAIL, "DNS ready endpoint without address"
                ready = True
        if ready and not has_53:
            return FAIL, "DNS ready endpoints without 53/TCP+UDP in same slice"
        if has_53 and ready:
            return PASS, "DNS ready with 53/TCP+UDP in same slice"
    return INCONCLUSIVE, "no ready DNS slice with 53/TCP+UDP"


def pred_hc_portal(doc):
    meta_gen = doc.get("metadata", {}).get("generation")
    obs_gen = doc.get("status", {}).get("observedGeneration")
    if not isinstance(meta_gen, int) or not isinstance(obs_gen, int):
        return INCONCLUSIVE, "generation missing"
    if obs_gen != meta_gen:
        return INCONCLUSIVE, "generation mismatch"
    spec_replicas = doc.get("spec", {}).get("replicas")
    st = doc.get("status", {})
    if spec_replicas == 1 and st.get("readyReplicas") == 1 and st.get("updatedReplicas") == 1 and st.get("availableReplicas") == 1:
        return PASS, "portal ready"
    return FAIL, "portal replicas not converged"


def pred_hc_gw(doc):
    meta_gen = doc.get("metadata", {}).get("generation")
    if not isinstance(meta_gen, int):
        return INCONCLUSIVE, "gateway generation missing"
    st = doc.get("status", {})
    conds = {c.get("type"): c for c in st.get("conditions", []) if isinstance(c, dict)}
    acc, prog = conds.get("Accepted"), conds.get("Programmed")
    if acc and prog and acc.get("status") == "True" and prog.get("status") == "True":
        if acc.get("observedGeneration") == meta_gen and prog.get("observedGeneration") == meta_gen:
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
        _count_transport(len(body))
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
    """5-request sample: Cluster -> Pod -> metrics -> same Pod -> same Cluster (30s hard deadline)."""
    start = time.monotonic()

    def raw(path):
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            raise ReadError("sample deadline exceeded")
        body, _ = run_kubectl_raw(kubectl, path, 5, 256 * 1024)
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            raise ReadError("sample deadline exceeded")
        _count_transport(len(body))
        return validate_envelope(body, False)

    try:
        cluster_path = "/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db"
        cluster = raw(cluster_path)
        primary = cluster.get("status", {}).get("currentPrimary")
        if not primary:
            return INCONCLUSIVE, "no currentPrimary", None
        if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", str(primary)):
            return INCONCLUSIVE, "invalid primary name", None
        pod_path = "/api/v1/namespaces/portal/pods/" + str(primary)
        pod = raw(pod_path)
        pod_ip = pod.get("status", {}).get("podIP")
        if not pod_ip:
            return INCONCLUSIVE, "pod IP missing", None
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            return INCONCLUSIVE, "sample deadline exceeded", None
        try:
            metrics_text = http_get("http://%s:9187/metrics" % pod_ip, wal.REQ_TIMEOUT, wal.METRIC_CAP).decode()
            _count_transport(len(metrics_text.encode()))
        except ReadError as e:
            return INCONCLUSIVE, str(e), None
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            return INCONCLUSIVE, "sample deadline exceeded", None
        pod_after = raw(pod_path)
        cluster_after = raw(cluster_path)
        disp, m, detail = wal.wal_sample(cluster, pod, metrics_text, cluster_after, pod_after,
                                         clock_evidence, baseline=gate.get("wal_baseline"),
                                         op_end_utc=gate.get("operation_end_utc"),
                                         gate_hash=gate.get("package_sha256"))
        return disp, detail, m
    except ReadError as e:
        return INCONCLUSIVE, str(e), None


def run_wal_window(kubectl, http_get, gate, state_dir, clock_evidence):
    """WAL observation window: <=3 samples at offsets 0/300/600s; baseline persists across slots."""
    baseline = gate.get("wal_baseline") or read_wal_baseline(state_dir, gate)
    for slot in range(wal.WINDOW_SLOTS):
        if slot > 0:
            time.sleep(300)
        wgate = dict(gate)
        if baseline is not None:
            wgate["wal_baseline"] = baseline
        res = run_wal_sample(kubectl, http_get, clock_evidence, wgate)
        if isinstance(res, tuple) and len(res) == 3:
            disp, detail, m = res
        else:
            disp, detail, m = res[0], res[1], None
        if m is not None:
            persist_wal_baseline(state_dir, gate, m)
            baseline = m
        if disp == PASS:
            return PASS, detail
        if disp == FAIL:
            return FAIL, detail
    return INCONCLUSIVE, "slots exhausted without fresh WAL progress"


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
    # stage ordering: only the successor of the last VERIFIED completed stage may run
    receipt_path = os.path.join(args.state_dir, "stage.receipt")
    last = read_receipt(receipt_path, gate)
    if args.stage != next_stage(last):
        print("STOP: stage out of order (expected %s)" % next_stage(last), file=sys.stderr)
        return 2
    # run/window authority keyed by stable package identity; retry within window allowed (<=3 slots)
    status, wst = open_window(gate, args.stage)
    if status == "blocked":
        print("STOP: " + str(wst), file=sys.stderr)
        return 2
    # output no-overwrite: pre-existing evidence is preserved
    out = Path(args.out)
    if out.exists():
        print("STOP: output already exists", file=sys.stderr)
        return 2

    readset = json.loads(READSET.read_text())
    journal = {"stage": args.stage, "context": CONTEXT, "reads": {}}
    try:
        budget = read_budget(args.state_dir)
    except ReadError as e:
        print("STOP: " + str(e), file=sys.stderr)
        return 2
    if budget_exhausted(budget):
        print("STOP: budget exhausted", file=sys.stderr)
        return 2
    _reset_transport()
    for read_id, spec in readset["reads"].items():
        if args.stage not in spec["stages"]:
            journal["reads"][read_id] = {"disposition": NOT_APPLICABLE}
            continue
        start = time.monotonic()
        try:
            if spec.get("method") == "wal":
                disp, detail = run_wal_window(args.kubectl, default_http_get, gate, args.state_dir, gate.get("clock_evidence"))
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

    executed = [v for v in journal["reads"].values() if v.get("disposition") != NOT_APPLICABLE]
    budget["requests"] = budget.get("requests", 0) + _TRANSPORT["requests"]
    budget["bytes"] = budget.get("bytes", 0) + _TRANSPORT["bytes"]
    budget["seconds"] = budget.get("seconds", 0.0) + sum(v.get("duration_ms", 0) for v in executed) / 1000.0
    write_budget(args.state_dir, budget)
    journal["budget"] = budget

    disp = [v.get("disposition") for v in journal["reads"].values()]
    agg = FAIL if FAIL in disp else (INCONCLUSIVE if INCONCLUSIVE in disp else (PASS if all(d in (PASS, NOT_APPLICABLE) for d in disp) else INCONCLUSIVE))
    journal["aggregate"] = agg
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(journal, sort_keys=True, indent=2))
    os.chmod(tmp, 0o600)
    os.replace(tmp, out)  # out does not exist (checked above); atomic publish
    if agg == PASS:
        write_receipt(receipt_path, gate, args.stage)
        complete_window(gate, args.stage)  # completed: never replayable
    else:
        # non-PASS: attempts already counted by open_window; budget persists; no completion.
        write_failure_state(args.state_dir, gate, args.stage, agg)
        fail_window(gate, args.stage)
        print("aggregate=%s" % agg)
        return 1
    print("aggregate=%s" % agg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
