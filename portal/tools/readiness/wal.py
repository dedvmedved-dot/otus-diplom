#!/usr/bin/env python3
"""Primary-bound WAL archive observation (OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER).

Source implementation; NOT a live execution grant. Implements the accepted
5-request sample (Cluster -> Pod -> metrics -> same Pod -> same Cluster), a
bounded no-redirect HTTP client for the exporter, pg_stat_archiver metric
parsing, per-request/per-window budget accounting, and a clock-skew validator.

Transports are injected (no live network); the production entry point does not
provide bypass flags.
"""
import hashlib
import json
import math
import re
import time

PASS = "PASS"
INCONCLUSIVE = "INCONCLUSIVE"
FAIL = "FAIL"

ARCHIVER_SERIES = [
    "cnpg_pg_stat_archiver_archived_count",
    "cnpg_pg_stat_archiver_failed_count",
    "cnpg_pg_stat_archiver_last_archived_time",
    "cnpg_pg_stat_archiver_last_failed_time",
    "cnpg_pg_stat_archiver_stats_reset_time",
]

# Normative budgets (from accepted R4 design)
WINDOW_SLOTS = 3           # offsets 0/300/600s
REQ_TIMEOUT = 5            # seconds per request
SAMPLE_DEADLINE = 30       # seconds per sample
WINDOW_DEADLINE = 660      # seconds per window
METADATA_CAP = 256 * 1024
METRIC_CAP = 1024 * 1024
SAMPLE_BODY_CAP = 2 * 1024 * 1024
WINDOW_REQ_CAP = 15
WINDOW_BODY_CAP = 6 * 1024 * 1024
CLOCK_SKEW_BOUND = 5       # seconds


class BudgetExceeded(Exception):
    pass


class ClockError(Exception):
    pass


class Budget:
    def __init__(self, window_req=WINDOW_REQ_CAP, window_bytes=WINDOW_BODY_CAP):
        self.requests = 0
        self.bytes = 0
        self.window_req = window_req
        self.window_bytes = window_bytes

    def charge(self, nbytes):
        self.requests += 1
        self.bytes += nbytes
        if self.requests > self.window_req or self.bytes > self.window_bytes:
            raise BudgetExceeded("window budget exceeded")


def parse_archiver_metrics(text):
    vals = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for name in ARCHIVER_SERIES:
            if line.startswith(name + " ") or line.startswith(name + "{"):
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        vals[name] = float(parts[1])
                    except ValueError:
                        vals[name] = float("nan")
    return vals


def fetch_metrics(pod_ip, http_get, budget):
    """Bounded GET to http://<pod_ip>:9187/metrics; no redirects, no env proxy."""
    url = "http://%s:9187/metrics" % pod_ip
    body = http_get(url, timeout=REQ_TIMEOUT, cap=METRIC_CAP)
    budget.charge(len(body))
    return body


def validate_clock(evidence, gate_hash=None):
    """Clock evidence contract: finite nonnegative numeric bound<=5, source/provenance,
    node/backend identity, observed time + validity, and (optional) hash-binding to the gate.

    A bare number or trusted=true flag is NOT clock evidence."""
    if not isinstance(evidence, dict):
        return False, "clock evidence missing"
    if evidence.get("trusted") is True:
        return False, "bare trusted flag is not provenance"
    bound = evidence.get("bound")
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        return False, "bound not numeric"
    try:
        b = float(bound)
    except (TypeError, ValueError):
        return False, "bound invalid"
    if math.isnan(b) or math.isinf(b) or b < 0:
        return False, "bound nonfinite/negative"
    if b > CLOCK_SKEW_BOUND:
        return False, "bound exceeds %ds" % CLOCK_SKEW_BOUND
    if not isinstance(evidence.get("source"), str) or not evidence["source"]:
        return False, "clock source missing"
    if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("provenance_sha256", ""))):
        return False, "clock provenance hash missing"
    if not isinstance(evidence.get("node"), str) or not evidence["node"]:
        return False, "clock node identity missing"
    if not isinstance(evidence.get("backend"), str) or not evidence["backend"]:
        return False, "clock backend identity missing"
    observed = evidence.get("observed_utc")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", str(observed)):
        return False, "clock observed_utc missing/invalid"
    if not isinstance(evidence.get("validity_hours"), int) or evidence["validity_hours"] <= 0:
        return False, "clock validity_hours invalid"
    if gate_hash is not None and evidence.get("gate_sha256") != gate_hash:
        return False, "clock evidence not bound to gate"
    return True, "clock evidence valid"


def wal_sample(cluster_doc, pod_doc, metrics_text, cluster_after, pod_after, clock_evidence, baseline=None, op_end_utc=None):
    """One 5-request sample; returns (disposition, metrics, detail)."""
    ok, detail = validate_clock(clock_evidence)
    if not ok:
        return INCONCLUSIVE, None, detail
    # identity bracket: same Cluster/Pod UID before and after; None is never equal to None.
    cu_before, cu_after = cluster_doc.get("metadata", {}).get("uid"), cluster_after.get("metadata", {}).get("uid")
    pu_before, pu_after = pod_doc.get("metadata", {}).get("uid"), pod_after.get("metadata", {}).get("uid")
    if cu_before is None or cu_after is None or cu_before != cu_after:
        return INCONCLUSIVE, None, "cluster UID missing/changed"
    if pu_before is None or pu_after is None or pu_before != pu_after:
        return INCONCLUSIVE, None, "pod UID missing/changed"
    if cluster_doc.get("status", {}).get("currentPrimary") != pod_doc.get("metadata", {}).get("name"):
        return INCONCLUSIVE, None, "pod is not currentPrimary"
    if not pod_doc.get("status", {}).get("podIP"):
        return INCONCLUSIVE, None, "pod IP missing"
    m = parse_archiver_metrics(metrics_text)
    missing = [s for s in ARCHIVER_SERIES if s not in m]
    if missing:
        return INCONCLUSIVE, m, "missing series: %s" % ",".join(missing)
    # nonfinite
    for k, v in m.items():
        if v != v or v in (float("inf"), float("-inf")):
            return INCONCLUSIVE, m, "nonfinite metric %s" % k
    # failure precedence over archive growth
    if baseline is not None:
        if m["cnpg_pg_stat_archiver_failed_count"] > baseline.get("cnpg_pg_stat_archiver_failed_count", 0):
            return FAIL, m, "failed_count grew"
        if m["cnpg_pg_stat_archiver_last_failed_time"] > baseline.get("cnpg_pg_stat_archiver_last_failed_time", 0):
            return FAIL, m, "last_failed_time advanced"
        if m["cnpg_pg_stat_archiver_stats_reset_time"] != baseline.get("cnpg_pg_stat_archiver_stats_reset_time", None):
            return INCONCLUSIVE, m, "stats reset"
        grown = m["cnpg_pg_stat_archiver_archived_count"] > baseline.get("cnpg_pg_stat_archiver_archived_count", 0)
        fresh = m["cnpg_pg_stat_archiver_last_archived_time"] > baseline.get("cnpg_pg_stat_archiver_last_archived_time", 0)
        if grown and fresh and op_end_utc is not None:
            if m["cnpg_pg_stat_archiver_last_archived_time"] > op_end_utc + CLOCK_SKEW_BOUND:
                return PASS, m, "fresh post-operation archive"
            return INCONCLUSIVE, m, "archive not after operation boundary"
        return INCONCLUSIVE, m, "no fresh archive progress"
    return PASS, m, "baseline sample recorded"
