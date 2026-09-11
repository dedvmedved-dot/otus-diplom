#!/usr/bin/env python3
"""
TASK-P7B2 — P7B2 verifier negative tests (offline, real logic).
Mirrors p7b2-final-readonly-verify.yml verification semantics.
"""

import json
import sys


def check_args(args):
    if any("kubelet-insecure-tls" in a for a in args):
        raise AssertionError("kubelet-insecure-tls present")
    if any("deprecated-kubelet-completely-insecure" in a for a in args):
        raise AssertionError("deprecated insecure present")
    if not any("kubelet-certificate-authority" in a for a in args):
        raise AssertionError("kubelet CA absent")


def check_image(req_image, iid, expected_digest="sha256:6231fb0a1ffab76c92ab880f51a0d11b290f688373647bcedff85af025dfd8a9"):
    if "v0.8.1" not in req_image:
        raise AssertionError("image version wrong")
    if expected_digest not in iid:
        raise AssertionError("image digest wrong")


def check_deploy(available):
    if available != 1:
        raise AssertionError("deployment unavailable")


def check_apiservice(available):
    if available != "True":
        raise AssertionError("apiservice unavailable")


def check_nodemetrics(items):
    if len(items) != 3:
        raise AssertionError(f"nodemetrics count {len(items)}")
    names = {i["metadata"]["name"] for i in items}
    for n in ("node-01", "node-02", "node-03"):
        if n not in names:
            raise AssertionError(f"{n} missing")
    for i in items:
        u = i.get("usage", {})
        if not u.get("cpu"):
            raise AssertionError("cpu empty")
        if not u.get("memory"):
            raise AssertionError("memory empty")
        if not i.get("timestamp"):
            raise AssertionError("timestamp missing")


def check_freshness(ts, now_ts):
    # stale if age > 120s (now_ts - ts > 120)
    if now_ts - ts > 120:
        raise AssertionError("stale timestamp")


def check_csr(pending):
    if pending > 0:
        raise AssertionError("pending serving CSR")


def check_kubelet_cfg(cfg):
    if "serverTLSBootstrap: true" not in cfg:
        raise AssertionError("serverTLSBootstrap=false")


def check_ca_trust(verify_rc):
    if verify_rc != 0:
        raise AssertionError("cluster-CA trust failure")


def check_route(route):
    if "172.30.20.0/24 via 172.30.140.1 dev bond0.140" not in route:
        raise AssertionError("P6D route missing")


def check_vlan143(out):
    if "bond0.143" not in out or "172.30.143" not in out:
        raise AssertionError("VLAN143 missing")


def check_velero(deps):
    if any("velero" in d for d in deps):
        raise AssertionError("Velero present")


def check_readme(data):
    seg = data.split("P7B2", 1)[-1].split("P7C", 1)[0]
    if "FINAL ACCEPTED" in seg:
        raise AssertionError("P7B2 falsely accepted")
    seg_c = data.split("P7C", 1)[-1].split("P8", 1)[0]
    if "AUTHORIZED" in seg_c and "NOT AUTHORIZED" not in seg_c:
        raise AssertionError("P7C authorized")


def check_gate_order(markers):
    # final PASS must not be emitted before all gates
    order = ["K8S", "NODES", "METRICS_SERVER", "APISERVICE", "NODE_METRICS", "TOP_NODES", "FINAL"]
    idx = [markers.index(m) for m in order if m in markers]
    if idx != sorted(idx):
        raise AssertionError("final PASS emitted before all gates")


GOOD_ARGS = ["--cert-dir=/tmp", "--secure-port=10250",
             "--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname",
             "--kubelet-use-node-status-port", "--metric-resolution=15s",
             "--kubelet-certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"]
GOOD_IID = "registry.k8s.io/metrics-server/metrics-server@sha256:6231fb0a1ffab76c92ab880f51a0d11b290f688373647bcedff85af025dfd8a9"
GOOD_REQ_IMAGE = "registry.k8s.io/metrics-server/metrics-server:v0.8.1@sha256:6231fb0a1ffab76c92ab880f51a0d11b290f688373647bcedff85af025dfd8a9"
GOOD_NM = {"items": [
    {"metadata": {"name": "node-01"}, "usage": {"cpu": "1n", "memory": "1Ki"}, "timestamp": "2026-09-11T23:00:00Z"},
    {"metadata": {"name": "node-02"}, "usage": {"cpu": "1n", "memory": "1Ki"}, "timestamp": "2026-09-11T23:00:00Z"},
    {"metadata": {"name": "node-03"}, "usage": {"cpu": "1n", "memory": "1Ki"}, "timestamp": "2026-09-11T23:00:00Z"},
]}

T = []
def t(name, expect_fail, fn):
    T.append((name, expect_fail, fn))

t("kubelet-insecure-tls present", True, lambda: check_args(["--kubelet-insecure-tls"]))
t("deprecated completely-insecure present", True, lambda: check_args(["--deprecated-kubelet-completely-insecure"]))
t("kubelet CA absent", True, lambda: check_args(["--secure-port=10250"]))
t("image version wrong", True, lambda: check_image("metrics-server@sha256:6231fb0a1ffab76c92ab880f51a0d11b290f688373647bcedff85af025dfd8a9", GOOD_IID))
t("image digest wrong", True, lambda: check_image(GOOD_REQ_IMAGE, "metrics-server@sha256:deadbeef"))
t("deployment unavailable", True, lambda: check_deploy(0))
t("apiservice unavailable", True, lambda: check_apiservice("False"))
t("nodemetrics count=2", True, lambda: check_nodemetrics(GOOD_NM["items"][:2]))
t("node-01 missing", True, lambda: check_nodemetrics([i for i in GOOD_NM["items"] if i["metadata"]["name"] != "node-01"]))
t("node-02 missing", True, lambda: check_nodemetrics([i for i in GOOD_NM["items"] if i["metadata"]["name"] != "node-02"]))
t("node-03 missing", True, lambda: check_nodemetrics([i for i in GOOD_NM["items"] if i["metadata"]["name"] != "node-03"]))
t("stale timestamp", True, lambda: check_freshness(1000, 2000))
t("cpu empty", True, lambda: check_nodemetrics([{"metadata":{"name":"node-01"},"usage":{"memory":"1Ki"},"timestamp":"t"}]))
t("memory empty", True, lambda: check_nodemetrics([{"metadata":{"name":"node-01"},"usage":{"cpu":"1n"},"timestamp":"t"}]))
t("pending kubelet-serving CSR", True, lambda: check_csr(1))
t("serverTLSBootstrap=false", True, lambda: check_kubelet_cfg("rotateCertificates: true"))
t("cluster-CA trust failure", True, lambda: check_ca_trust(1))
t("P6D route missing", True, lambda: check_route("default via 192.168.194.1"))
t("VLAN143 missing", True, lambda: check_vlan143("bond0.140"))
t("Velero present", True, lambda: check_velero(["velero"]))
t("README falsely P7B2 FINAL ACCEPTED", True, lambda: check_readme("P7B2 FINAL ACCEPTED\nP7C NOT AUTHORIZED\nP8 NOT AUTHORIZED"))
t("README authorizes P7C", True, lambda: check_readme("P7B2 IN PROGRESS\nP7C AUTHORIZED\nP8 NOT AUTHORIZED"))
t("final PASS before gates", True, lambda: check_gate_order(["FINAL", "K8S", "NODES"]))
t("clean fixture", False, lambda: (check_args(GOOD_ARGS), check_image(GOOD_REQ_IMAGE, GOOD_IID), check_deploy(1), check_apiservice("True"), check_nodemetrics(GOOD_NM["items"]), check_csr(0), check_kubelet_cfg("serverTLSBootstrap: true"), check_ca_trust(0), check_route("172.30.20.0/24 via 172.30.140.1 dev bond0.140"), check_vlan143("bond0.143 172.30.143.1"), check_velero([]), check_readme("P7B2 IN PROGRESS\nP7C NOT AUTHORIZED\nP8 NOT AUTHORIZED"), check_gate_order(["K8S","NODES","METRICS_SERVER","APISERVICE","NODE_METRICS","TOP_NODES","FINAL"])))


def main():
    total = 0
    failed = 0
    for name, expect_fail, fn in T:
        total += 1
        actual = "PASS"
        try:
            fn()
        except Exception as e:
            actual = "FAIL"
        ok = (actual == ("FAIL" if expect_fail else "PASS"))
        print(f"--- {name} --- expected={'FAIL' if expect_fail else 'PASS'} actual={actual} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            failed += 1
    print(f"\nNEGATIVE_TESTS_TOTAL={total}")
    print(f"NEGATIVE_TESTS_FAILED={failed}")
    print(f"HARNESS_EXIT={0 if failed == 0 else 1}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
