#!/usr/bin/env python3
"""
TASK-P7B2-R1 — Shared validation logic for Metrics Server 0.8.1.
Pure, side-effect-free validation functions (raise AssertionError on FAIL).

Used by BOTH:
  - ansible/playbooks/p7b2-final-readonly-verify.yml (real verifier)
  - ansible/tests/p7b2_verifier_negative_tests.py (negative harness)

Single source of truth — do NOT maintain a parallel copy.
"""

from datetime import datetime, timedelta, timezone

EXPECTED_DIGEST = "sha256:6231fb0a1ffab76c92ab880f51a0d11b290f688373647bcedff85af025dfd8a9"
NODE_NAMES = ("node-01", "node-02", "node-03")


def validate_args(args):
    """Secure kubelet args: no insecure flags, explicit kubelet CA present."""
    if any("kubelet-insecure-tls" in a for a in args):
        raise AssertionError("--kubelet-insecure-tls present")
    if any("deprecated-kubelet-completely-insecure" in a for a in args):
        raise AssertionError("--deprecated-kubelet-completely-insecure present")
    if not any("kubelet-certificate-authority" in a for a in args):
        raise AssertionError("--kubelet-certificate-authority absent")


def validate_image(req_image, iid, expected_digest=EXPECTED_DIGEST):
    """Requested image must carry v0.8.1; live imageID must carry exact digest."""
    if "v0.8.1" not in req_image:
        raise AssertionError("image version wrong")
    if expected_digest not in iid:
        raise AssertionError("image digest wrong")


def validate_deploy(ready, replicas):
    if ready != 1 or replicas != 1:
        raise AssertionError(f"deployment not 1/1: {ready}/{replicas}")


def validate_apiservice(available):
    if available != "True":
        raise AssertionError(f"apiservice not Available: {available}")


def validate_nodemetrics(obj):
    """Validate NodeMetricsList: 3 items, node-01/02/03, cpu/memory/timestamp/window."""
    assert obj.get("kind") == "NodeMetricsList", "kind != NodeMetricsList"
    items = obj.get("items")
    assert isinstance(items, list), "items not list"
    assert len(items) == 3, f"node metrics count {len(items)}"
    names = {i["metadata"]["name"] for i in items}
    for n in NODE_NAMES:
        assert n in names, f"{n} missing"
    for i in items:
        u = i.get("usage", {})
        assert u.get("cpu"), f"{i['metadata']['name']} cpu empty"
        assert u.get("memory"), f"{i['metadata']['name']} memory empty"
        assert i.get("timestamp"), f"{i['metadata']['name']} timestamp missing"
        assert i.get("window"), f"{i['metadata']['name']} window missing"


def _parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def validate_freshness(obj, now=None):
    """Every NodeMetrics item: not >10s future, age <=120s, window > 0."""
    if now is None:
        now = datetime.now(timezone.utc)
    for i in obj["items"]:
        ts = i["timestamp"]
        t = _parse_ts(ts)
        if t > now + timedelta(seconds=10):
            raise AssertionError(f"{i['metadata']['name']} timestamp >10s future")
        age = (now - t).total_seconds()
        if age > 120:
            raise AssertionError(f"{i['metadata']['name']} stale (age {age:.0f}s)")
        w = i.get("window", "")
        if not w:
            raise AssertionError(f"{i['metadata']['name']} window missing")
        try:
            wf = float(w.rstrip("s"))
        except ValueError:
            raise AssertionError(f"{i['metadata']['name']} window malformed: {w}")
        if wf <= 0:
            raise AssertionError(f"{i['metadata']['name']} window zero/invalid")


def validate_top_nodes(output, required=NODE_NAMES):
    for n in required:
        assert n in output, f"top nodes missing {n}"


def validate_top_pods(output):
    lines = [l for l in output.splitlines() if l.strip() and not l.startswith("NAMESPACE")]
    if len(lines) < 1:
        raise AssertionError("kubectl top pods -A empty (no data rows)")


def validate_csr(items):
    pending = [c for c in items
               if c["spec"].get("signerName") == "kubernetes.io/kubelet-serving"
               and not any(cond.get("type") in ("Approved", "Denied")
                           for cond in c["status"].get("conditions", []))]
    if pending:
        raise AssertionError(f"pending kubelet-serving CSR: {len(pending)}")


def validate_kubelet_cfg(cfg):
    if "serverTLSBootstrap: true" not in cfg:
        raise AssertionError("serverTLSBootstrap false")
    if "rotateCertificates: true" not in cfg:
        raise AssertionError("rotateCertificates false")


def validate_ca_trust(verify_rc):
    if verify_rc != 0:
        raise AssertionError("cluster-CA trust failure")


def validate_route(route):
    if "172.30.20.0/24 via 172.30.140.1 dev bond0.140" not in route:
        raise AssertionError("P6D route missing")


def validate_vlan143(out):
    if "bond0.143" not in out or "172.30.143" not in out:
        raise AssertionError("VLAN143 missing")


def validate_velero(deps):
    if any("velero" in d for d in deps):
        raise AssertionError("Velero unexpectedly present")


def validate_readme(data):
    if "P7B1" not in data or "FINAL ACCEPTED" not in data:
        raise AssertionError("P7B1 not FINAL ACCEPTED")
    if "P7B2" not in data or "IN PROGRESS" not in data:
        raise AssertionError("P7B2 not IN PROGRESS")
    if "P7C" not in data or "NOT AUTHORIZED" not in data:
        raise AssertionError("P7C not NOT AUTHORIZED")
    if "P8" not in data or "NOT AUTHORIZED" not in data:
        raise AssertionError("P8 not NOT AUTHORIZED")
    seg = data.split("P7B2", 1)[-1].split("P7C", 1)[0]
    if "FINAL ACCEPTED" in seg:
        raise AssertionError("P7B2 falsely FINAL ACCEPTED")
    seg_c = data.split("P7C", 1)[-1].split("P8", 1)[0]
    if "AUTHORIZED" in seg_c and "NOT AUTHORIZED" not in seg_c:
        raise AssertionError("P7C falsely authorized")


def validate_recovery(old_uid, new_uid, apiservice_recovered, metrics_recovered, top_nodes_output):
    if not old_uid:
        raise AssertionError("recovery old UID missing")
    if not new_uid:
        raise AssertionError("recovery new UID missing")
    if old_uid == new_uid:
        raise AssertionError("recovery UID unchanged")
    if apiservice_recovered != "YES":
        raise AssertionError("recovery APIService marker not YES")
    if metrics_recovered != "YES":
        raise AssertionError("recovery NodeMetrics marker not YES")
    for n in NODE_NAMES:
        if n not in top_nodes_output:
            raise AssertionError(f"recovery top nodes missing {n}")


def validate_gate_order(markers):
    """final PASS must not be emitted before all gates."""
    order = ["K8S", "NODES", "METRICS_SERVER", "APISERVICE", "NODE_METRICS",
             "FRESHNESS", "TOP_NODES", "TOP_PODS", "RECOVERY", "FINAL"]
    present = [m for m in order if m in markers]
    idx = [markers.index(m) for m in present]
    if idx != sorted(idx):
        raise AssertionError("final PASS emitted before all gates")
