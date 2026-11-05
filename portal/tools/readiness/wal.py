#!/usr/bin/env python3
"""Primary-bound WAL archive observation (OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER).

Source implementation; NOT a live execution grant. Implements the accepted
5-request sample (Cluster -> Pod -> metrics -> same Pod -> same Cluster), a
bounded no-redirect/no-proxy HTTP client for the exporter, pg_stat_archiver
metric parsing with duplicate/nonfinite/future rejection, per-request/per-window
budget accounting, and a clock-evidence validator (typed provenance, node/backend
identity, observed time + validity + expiry).

Transports are injected (no live network); the production entry point does not
provide bypass flags.
"""
import calendar
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


class Scheduler:
    """WAL observation scheduler: 6 windows (S0 baseline + S1..S4), <=3 slots per window
    at offsets 0/300/600s, cumulative request/byte/time budgets. Virtual-clock testable
    (no wall sleep): advance the clock explicitly between slot calls."""

    def __init__(self):
        self.windows = 0
        self.slot = 0
        self.baseline = None
        self.budget = {"requests": 0, "bytes": 0, "seconds": 0.0}
        self.total_requests = 0
        self.total_bytes = 0
        self.total_seconds = 0.0

    def next_slot_offset(self):
        return [0, 300, 600][self.slot]

    def can_sample(self):
        return self.slot < WINDOW_SLOTS

    def advance_slot(self):
        if self.slot + 1 < WINDOW_SLOTS:
            self.slot += 1
            return True
        return False

    def record_sample(self, disposition, metrics, requests, bytes_, seconds):
        self.budget["requests"] += requests
        self.budget["bytes"] += bytes_
        self.budget["seconds"] += seconds
        self.total_requests += requests
        self.total_bytes += bytes_
        self.total_seconds += seconds
        if disposition == PASS and metrics is not None:
            self.baseline = metrics

    def budget_exceeded(self):
        return (self.budget["requests"] > WINDOW_REQ_CAP or self.budget["bytes"] > WINDOW_BODY_CAP
                or self.total_requests > 90 or self.total_bytes > 36 * 1024 * 1024
                or self.total_seconds > 3960)


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
    """Returns (values, duplicates). A duplicated series is invalid (no last-wins)."""
    vals = {}
    duplicates = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for name in ARCHIVER_SERIES:
            if line.startswith(name + " ") or line.startswith(name + "{"):
                if name in vals:
                    duplicates.add(name)
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        vals[name] = float(parts[1])
                    except ValueError:
                        vals[name] = float("nan")
    return vals, duplicates


def fetch_metrics(pod_ip, http_get, budget):
    url = "http://%s:9187/metrics" % pod_ip
    body = http_get(url, timeout=REQ_TIMEOUT, cap=METRIC_CAP)
    budget.charge(len(body))
    return body


def validate_clock(evidence, gate_hash=None, now=None):
    """Clock evidence contract: finite nonnegative numeric bound<=5, source/provenance,
    node/backend identity, observed time + validity + expiry, optional hash-binding.

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
    try:
        obs_epoch = calendar.timegm(time.strptime(str(observed), "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return False, "clock observed_utc unparsable"
    if now is None:
        now = time.time()
    if obs_epoch > now + CLOCK_SKEW_BOUND:
        return False, "clock observed_utc in the future"
    if obs_epoch + evidence["validity_hours"] * 3600 < now:
        return False, "clock evidence expired"
    if gate_hash is not None and evidence.get("gate_sha256") != gate_hash:
        return False, "clock evidence not bound to gate"
    return True, "clock evidence valid"


def wal_sample(cluster_doc, pod_doc, metrics_text, cluster_after, pod_after, clock_evidence,
               baseline=None, op_end_utc=None, now=None, gate_hash=None):
    """One 5-request sample; returns (disposition, metrics, detail)."""
    ok, detail = validate_clock(clock_evidence, gate_hash=gate_hash, now=now)
    if not ok:
        return INCONCLUSIVE, None, detail
    if now is None:
        now = time.time()
    # identity bracket: same Cluster/Pod UID before/after; None never equals None.
    cu_b, cu_a = cluster_doc.get("metadata", {}).get("uid"), cluster_after.get("metadata", {}).get("uid")
    pu_b, pu_a = pod_doc.get("metadata", {}).get("uid"), pod_after.get("metadata", {}).get("uid")
    if cu_b is None or cu_a is None or cu_b != cu_a:
        return INCONCLUSIVE, None, "cluster UID missing/changed"
    if pu_b is None or pu_a is None or pu_b != pu_a:
        return INCONCLUSIVE, None, "pod UID missing/changed"
    # primary must be the SAME before and after the metrics fetch
    if cluster_after.get("status", {}).get("currentPrimary") != cluster_doc.get("status", {}).get("currentPrimary"):
        return INCONCLUSIVE, None, "currentPrimary changed after sample"
    if cluster_doc.get("status", {}).get("currentPrimary") != pod_doc.get("metadata", {}).get("name"):
        return INCONCLUSIVE, None, "pod is not currentPrimary"
    # pod IP / restart / owner binding must be stable AND bound to the Cluster
    if pod_after.get("status", {}).get("podIP") != pod_doc.get("status", {}).get("podIP"):
        return INCONCLUSIVE, None, "pod IP changed after sample"
    def owner_uid(p):
        refs = p.get("metadata", {}).get("ownerReferences", []) or []
        return refs[0].get("uid") if refs else None
    ou_before, ou_after = owner_uid(pod_doc), owner_uid(pod_after)
    if ou_before is None or ou_after is None:
        return INCONCLUSIVE, None, "pod owner reference missing"
    if ou_before != ou_after:
        return INCONCLUSIVE, None, "pod owner changed"
    if ou_before != cluster_doc.get("metadata", {}).get("uid"):
        return INCONCLUSIVE, None, "pod owner not bound to cluster"
    def restart(p):
        cs = p.get("status", {}).get("containerStatuses", []) or []
        return cs[0].get("restartCount", 0) if cs else 0
    if restart(pod_after) != restart(pod_doc):
        return INCONCLUSIVE, None, "pod restart changed"
    # node binding: clock evidence must match the sampled pod's node
    if clock_evidence.get("node") != pod_doc.get("spec", {}).get("nodeName"):
        return INCONCLUSIVE, None, "clock node does not match pod node"
    m, duplicates = parse_archiver_metrics(metrics_text)
    if duplicates:
        return INCONCLUSIVE, m, "duplicate metric series: %s" % ",".join(sorted(duplicates))
    missing = [s for s in ARCHIVER_SERIES if s not in m]
    if missing:
        return INCONCLUSIVE, m, "missing series: %s" % ",".join(missing)
    for k, v in m.items():
        if v != v or v in (float("inf"), float("-inf")):
            return INCONCLUSIVE, m, "nonfinite metric %s" % k
    # future timestamp (relative to sample time) is invalid
    if m["cnpg_pg_stat_archiver_last_archived_time"] > now + CLOCK_SKEW_BOUND:
        return INCONCLUSIVE, m, "future last_archived_time"
    if m["cnpg_pg_stat_archiver_last_failed_time"] > now + CLOCK_SKEW_BOUND:
        return INCONCLUSIVE, m, "future last_failed_time"
    # first baseline sample is NOT proof of new WAL progress
    if baseline is None:
        return INCONCLUSIVE, m, "baseline sample recorded (no progress proof)"
    if m["cnpg_pg_stat_archiver_failed_count"] > baseline.get("cnpg_pg_stat_archiver_failed_count", 0):
        return FAIL, m, "failed_count grew"
    if m["cnpg_pg_stat_archiver_last_failed_time"] > baseline.get("cnpg_pg_stat_archiver_last_failed_time", 0):
        return FAIL, m, "last_failed_time advanced"
    if m["cnpg_pg_stat_archiver_stats_reset_time"] != baseline.get("cnpg_pg_stat_archiver_stats_reset_time", None):
        return INCONCLUSIVE, m, "stats reset"
    grown = m["cnpg_pg_stat_archiver_archived_count"] > baseline.get("cnpg_pg_stat_archiver_archived_count", 0)
    fresh = m["cnpg_pg_stat_archiver_last_archived_time"] > baseline.get("cnpg_pg_stat_archiver_last_archived_time", 0)
    if grown and fresh:
        if op_end_utc is not None:
            if m["cnpg_pg_stat_archiver_last_archived_time"] > op_end_utc + CLOCK_SKEW_BOUND:
                return PASS, m, "fresh post-operation archive"
            return INCONCLUSIVE, m, "archive not after operation boundary"
        return PASS, m, "fresh archive progress"
    return INCONCLUSIVE, m, "no fresh archive progress"
