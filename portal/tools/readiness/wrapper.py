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
import fcntl
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


def gate_identity_sha256(gate):
    """Deterministic identity hash of the gate's binding fields — NOT the package hash.
    Clock evidence must bind to THIS gate, not to any gate sharing the same package bytes."""
    fields = {k: gate.get(k) for k in ("source_sha", "package_sha256", "issued_at_utc",
                                       "expiry_hours", "mode", "context")}
    return sha256_hex(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode())


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


RESERVATION_BASE = os.environ.get("P8C_READINESS_BASE", os.path.join(tempfile.gettempdir(), "p8c-readiness"))

# Budget levels (accepted R4 design): overall vs WAL-cumulative vs window vs sample.
OVERALL_REQ_CAP = 233
OVERALL_BODY_CAP = 179 * 1024 * 1024
OVERALL_SEC_CAP = 5265.0
WAL_REQ_CAP = 90
WAL_BODY_CAP = 36 * 1024 * 1024
WAL_SEC_CAP = 3960.0

_TRANSPORT = {"requests": 0, "bytes": 0, "seconds": 0.0}
_WAL_TRANSPORT = {"requests": 0, "bytes": 0, "seconds": 0.0}
_BUDGET_BASE = {"requests": 0, "bytes": 0, "seconds": 0.0,
                "wal_requests": 0, "wal_bytes": 0, "wal_seconds": 0.0}
_READ_CACHE = {}
_BUDGET_CONTEXT = {"gate": None, "state_dir": None, "budget": None}


def _set_budget_context(gate, state_dir, budget):
    global _BUDGET_CONTEXT
    _BUDGET_CONTEXT = {"gate": gate, "state_dir": state_dir, "budget": budget}


_BUDGET_FIELDS = ("requests", "bytes", "seconds", "wal_requests", "wal_bytes", "wal_seconds")


def _load_budget_file(p):
    if not os.path.exists(p):
        return {f: 0 for f in _BUDGET_FIELDS}
    try:
        b = json.loads(Path(p).read_text())
    except Exception:
        raise ReadError("budget state corrupt")
    if not isinstance(b, dict):
        raise ReadError("budget state corrupt")
    for f in _BUDGET_FIELDS:
        if not _finite_nonnegative(b.get(f, 0)):
            raise ReadError("budget state not finite/nonnegative (corrupt)")
    return b


def _write_budget_file(p, budget):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(budget, f, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)
    dirfd = os.open(os.path.dirname(p), os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def _charge(gate, field, delta, cap, commit=True):
    """Atomically reserve+commit `delta` to one monotonic budget field under the authority lock.

    The whole check-remaining/reserve/commit is serialized, so two independent charges are
    additive (both count) and a single remaining slot cannot be spent twice.

    `commit` controls overrun semantics: for continuous consumption (bytes/seconds) the consumed
    delta is RECORDED even when it crosses the cap (a failure must not turn into "nothing was
    consumed"); for discrete reservations (requests) the slot is not recorded when the cap would
    be exceeded (the slot is not spent)."""
    p = budget_path(gate)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    lock = open(p + ".lock", "a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current = _load_budget_file(p)
        new_val = current.get(field, 0) + delta
        if new_val > cap:
            if commit:
                current[field] = new_val  # preserve the actually-consumed delta on overrun
                _write_budget_file(p, current)
            raise ReadError("budget exhausted")
        current[field] = new_val
        _write_budget_file(p, current)
        return current
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def _reset_transport():
    global _TRANSPORT, _WAL_TRANSPORT
    _TRANSPORT = {"requests": 0, "bytes": 0, "seconds": 0.0}
    _WAL_TRANSPORT = {"requests": 0, "bytes": 0, "seconds": 0.0}


def _set_budget_base(budget):
    global _BUDGET_BASE
    _BUDGET_BASE = {
        "requests": budget.get("requests", 0),
        "bytes": budget.get("bytes", 0),
        "seconds": budget.get("seconds", 0.0),
        "wal_requests": budget.get("wal_requests", 0),
        "wal_bytes": budget.get("wal_bytes", 0),
        "wal_seconds": budget.get("wal_seconds", 0.0),
    }


def _authority_exhausted(gate, overall=True):
    """Consult the on-disk authority for a terminal exhaustion signal (recorded overruns count)."""
    if gate is None:
        return False
    try:
        b = _load_budget_file(budget_path(gate))
    except ReadError:
        return True  # corrupt authority -> fail closed
    if overall:
        return (b.get("requests", 0) >= OVERALL_REQ_CAP
                or b.get("bytes", 0) >= OVERALL_BODY_CAP
                or b.get("seconds", 0.0) >= OVERALL_SEC_CAP)
    return (b.get("wal_requests", 0) >= WAL_REQ_CAP
            or b.get("wal_bytes", 0) >= WAL_BODY_CAP
            or b.get("wal_seconds", 0.0) >= WAL_SEC_CAP)


def _overall_exhausted():
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None and _authority_exhausted(gate, True):
        return True
    return (_BUDGET_BASE["requests"] + _TRANSPORT["requests"] >= OVERALL_REQ_CAP
            or _BUDGET_BASE["bytes"] + _TRANSPORT["bytes"] >= OVERALL_BODY_CAP
            or _BUDGET_BASE["seconds"] + _TRANSPORT["seconds"] >= OVERALL_SEC_CAP)


def _wal_exhausted():
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None and _authority_exhausted(gate, False):
        return True
    return (_BUDGET_BASE["wal_requests"] + _WAL_TRANSPORT["requests"] >= WAL_REQ_CAP
            or _BUDGET_BASE["wal_bytes"] + _WAL_TRANSPORT["bytes"] >= WAL_BODY_CAP
            or _BUDGET_BASE["wal_seconds"] + _WAL_TRANSPORT["seconds"] >= WAL_SEC_CAP)


def _reset_read_cache():
    global _READ_CACHE
    _READ_CACHE = {}


def _count_request():
    global _TRANSPORT
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None:
        if _overall_exhausted():
            raise ReadError("overall budget exhausted")
        _charge(gate, "requests", 1, OVERALL_REQ_CAP, commit=False)
    _TRANSPORT["requests"] += 1


def _count_bytes(n):
    global _TRANSPORT
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None:
        _charge(gate, "bytes", int(n), OVERALL_BODY_CAP)
    _TRANSPORT["bytes"] += int(n)


def _count_wal_request():
    global _WAL_TRANSPORT
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None:
        if _wal_exhausted():
            raise ReadError("WAL budget exhausted")
        _charge(gate, "wal_requests", 1, WAL_REQ_CAP, commit=False)
    _WAL_TRANSPORT["requests"] += 1


def _count_wal_bytes(n):
    global _WAL_TRANSPORT
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None:
        _charge(gate, "wal_bytes", int(n), WAL_BODY_CAP)
    _WAL_TRANSPORT["bytes"] += int(n)


def _count_wal(nbytes, seconds):
    """WAL-cumulative budget accounting (subset of overall, tracked separately)."""
    global _TRANSPORT, _WAL_TRANSPORT
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None:
        _charge(gate, "requests", 1, OVERALL_REQ_CAP, commit=False)
        _charge(gate, "bytes", int(nbytes), OVERALL_BODY_CAP)
        _charge(gate, "wal_requests", 1, WAL_REQ_CAP, commit=False)
        _charge(gate, "wal_bytes", int(nbytes), WAL_BODY_CAP)
        _charge(gate, "wal_seconds", float(seconds), WAL_SEC_CAP)
    _TRANSPORT["requests"] += 1
    _TRANSPORT["bytes"] += int(nbytes)
    _WAL_TRANSPORT["requests"] += 1
    _WAL_TRANSPORT["bytes"] += int(nbytes)
    _WAL_TRANSPORT["seconds"] += float(seconds)


def _count_wal_seconds(seconds):
    global _WAL_TRANSPORT
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None:
        try:
            _charge(gate, "wal_seconds", float(seconds), WAL_SEC_CAP)
        except ReadError:
            pass
    _WAL_TRANSPORT["seconds"] += float(seconds)


# In-flight WAL tracking: while a WAL sample is executing, its elapsed time is not yet durable
# (charged in the sample's finally), so remaining-WAL-time decisions must also subtract the
# in-flight elapsed, and the transport layer must know whether the current read is a WAL read.
_WAL_ACTIVE = [False]
_WAL_SAMPLE_START = [None]


def _charge_partial(total, wal=True):
    """Durable-charge a partial body into every applicable counter. An overrun in one counter
    (already recorded durably by _charge) must NOT prevent the remaining counters from recording
    the same consumption before the terminal outcome is raised."""
    if total <= 0:
        return
    counters = [_count_bytes]
    if wal:
        counters.append(_count_wal_bytes)
    for fn in counters:
        try:
            fn(total)
        except ReadError:
            pass


def _authority_budget():
    """Return the current on-disk authority budget, or None when no gate is bound.

    Remaining-capacity decisions use the CURRENT authority (recorded overruns included), not the
    process-local base+transport which can be stale relative to a completed concurrent charge."""
    gate = _BUDGET_CONTEXT["gate"]
    if gate is None:
        return None
    try:
        return _load_budget_file(budget_path(gate))
    except ReadError:
        return None


def _remaining_body():
    b = _authority_budget()
    if b is not None:
        return OVERALL_BODY_CAP - b.get("bytes", 0)
    return OVERALL_BODY_CAP - (_BUDGET_BASE["bytes"] + _TRANSPORT["bytes"])


def _remaining_seconds():
    b = _authority_budget()
    if b is not None:
        return OVERALL_SEC_CAP - b.get("seconds", 0.0)
    return OVERALL_SEC_CAP - (_BUDGET_BASE["seconds"] + _TRANSPORT["seconds"])


def _remaining_wal_body():
    b = _authority_budget()
    if b is not None:
        return WAL_BODY_CAP - b.get("wal_bytes", 0)
    return WAL_BODY_CAP - (_BUDGET_BASE["wal_bytes"] + _WAL_TRANSPORT["bytes"])


def _remaining_wal_seconds():
    inflight = 0.0
    if _WAL_SAMPLE_START[0] is not None:
        inflight = time.monotonic() - _WAL_SAMPLE_START[0]
    b = _authority_budget()
    if b is not None:
        return WAL_SEC_CAP - b.get("wal_seconds", 0.0) - inflight
    return WAL_SEC_CAP - (_BUDGET_BASE["wal_seconds"] + _WAL_TRANSPORT["seconds"] + inflight)


def _count_seconds(n):
    global _TRANSPORT
    gate = _BUDGET_CONTEXT["gate"]
    if gate is not None:
        _charge(gate, "seconds", float(n), OVERALL_SEC_CAP)
    _TRANSPORT["seconds"] += float(n)


def _count_transport(nbytes):
    _count_request()
    _count_bytes(nbytes)


def _io_call(fn, *args, **kwargs):
    """Run a transport call and charge its actual elapsed time to the overall seconds budget.

    The elapsed (not just explicit sleeps) is part of the consumed I/O budget; it must not be
    lost. The charge is recorded in a finally so a transport error still accounts for the time
    spent inside the I/O. An overrun in the elapsed charge is recorded durably but NOT raised
    here — the caller must still receive the body so it can account the actual received bytes
    before a terminal outcome; the exhausted budget is then detected by the next permit check."""
    t0 = time.monotonic()
    try:
        return fn(*args, **kwargs)
    finally:
        try:
            _count_seconds(time.monotonic() - t0)
        except ReadError:
            pass  # overrun already recorded durably by _charge


def budget_path(gate):
    """Budget is keyed by stable package identity (not state/output path)."""
    return os.path.join(RESERVATION_BASE, str(gate.get("package_sha256", ""))[:32], "budget.json")


def _finite_nonnegative(value):
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    import math
    return not (math.isnan(f) or math.isinf(f)) and f >= 0


def budget_valid(budget):
    for k in ("requests", "bytes", "seconds", "wal_requests", "wal_bytes", "wal_seconds"):
        if not _finite_nonnegative(budget.get(k, 0)):
            return False
    return True


def budget_exhausted(budget):
    if budget.get("requests", 0) >= OVERALL_REQ_CAP or budget.get("bytes", 0) >= OVERALL_BODY_CAP \
            or budget.get("seconds", 0.0) >= OVERALL_SEC_CAP:
        return True
    if budget.get("wal_requests", 0) >= WAL_REQ_CAP or budget.get("wal_bytes", 0) >= WAL_BODY_CAP \
            or budget.get("wal_seconds", 0.0) >= WAL_SEC_CAP:
        return True
    return False


def reservation_path(gate, stage):
    """Stable one-run authority location: keyed by package identity, NOT state/output path."""
    return os.path.join(RESERVATION_BASE, str(gate.get("package_sha256", ""))[:32], stage + ".window.json")


def read_window_state(path):
    if not os.path.exists(path):
        return None
    try:
        return json.loads(Path(path).read_text())
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
        if status == "failed":
            return "blocked", "window exhausted (no retry)"
        return "blocked", "window state invalid"
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
    st["status"] = "failed"
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
        r = json.loads(Path(receipt_path).read_text())
    except Exception:
        return None
    if not isinstance(r, dict):
        return None
    if r.get("source_sha") != gate.get("source_sha") or r.get("package_sha256") != gate.get("package_sha256"):
        return None
    if r.get("issued_at_utc") != gate.get("issued_at_utc"):
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


def read_budget(gate, state_dir=None):
    """Budget is the cumulative (общий) consumption, stored at the stable authority (package-keyed);
    a legacy state-dir budget.json is merged as a pre-write override (MAX per monotonic field)."""
    budget = {"requests": 0, "bytes": 0, "seconds": 0.0,
              "wal_requests": 0, "wal_bytes": 0, "wal_seconds": 0.0}
    sources = [budget_path(gate)]
    if state_dir is not None:
        sources.append(os.path.join(state_dir, "budget.json"))
    for src in sources:
        if not os.path.exists(src):
            continue
        try:
            b = json.loads(Path(src).read_text())
        except Exception:
            raise ReadError("budget state corrupt")
        if not isinstance(b, dict):
            raise ReadError("budget state corrupt")
        for k in budget:
            v = b.get(k, budget[k])
            if not _finite_nonnegative(v):
                raise ReadError("budget state not finite/nonnegative (corrupt)")
            budget[k] = max(budget[k], v)
    return budget


def write_budget(gate, budget):
    """Persist cumulative consumption to the stable authority.

    Serialized read-modify-write (fcntl.flock on a sidecar lock file) + fsync of file and
    directory, and a MAX merge per monotonic field, so concurrent processes cannot lose an
    update and a crash after a counter increment cannot silently drop it."""
    p = budget_path(gate)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    lock = open(p + ".lock", "a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current = {}
        if os.path.exists(p):
            try:
                current = json.loads(Path(p).read_text())
            except Exception:
                raise ReadError("budget state corrupt")
        if not isinstance(current, dict):
            raise ReadError("budget state corrupt")
        merged = dict(budget)
        for k in merged:
            if k in current:
                if not _finite_nonnegative(current[k]) or not _finite_nonnegative(merged[k]):
                    raise ReadError("budget state not finite/nonnegative (corrupt)")
                merged[k] = max(merged[k], current[k])
        tmp = p + ".tmp"
        with open(tmp, "w") as f:
            json.dump(merged, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)
        dirfd = os.open(os.path.dirname(p), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def persist_wal_baseline(state_dir, gate, metrics, pod_uid=None, observed_at=None):
    """Persist the latest WAL archive metrics as the baseline for the next stage's sample."""
    p = os.path.join(state_dir, "wal-baseline.json")
    rec = {"source_sha": gate.get("source_sha"), "package_sha256": gate.get("package_sha256"),
           "issued_at_utc": gate.get("issued_at_utc"), "metrics": metrics,
           "pod_uid": pod_uid, "observed_at": observed_at}
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
        rec = json.loads(Path(p).read_text())
    except Exception:
        return None
    if rec.get("source_sha") == gate.get("source_sha") and rec.get("package_sha256") == gate.get("package_sha256"):
        return rec.get("metrics")
    return None


def read_wal_baseline_record(state_dir, gate):
    p = os.path.join(state_dir, "wal-baseline.json")
    if not os.path.exists(p):
        return None
    try:
        rec = json.loads(Path(p).read_text())
    except Exception:
        return None
    if rec.get("source_sha") == gate.get("source_sha") and rec.get("package_sha256") == gate.get("package_sha256"):
        return rec
    return None


def read_slot_count(state_dir, stage):
    p = os.path.join(state_dir, stage + ".slots.json")
    if not os.path.exists(p):
        return 0
    try:
        return int(json.loads(Path(p).read_text()).get("attempted", 0))
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
    hard_deadline = time.monotonic() + timeout
    chunks = []
    total = 0
    fd = proc.stdout.fileno()
    timed_out = False
    try:
        while total < cap:
            remain = hard_deadline - time.monotonic()
            if remain <= 0:
                timed_out = True
                break
            r, _, _ = select.select([fd], [], [], max(0.0, remain))
            if fd not in r:
                if proc.poll() is not None:
                    break
                continue
            buf = os.read(fd, min(65536, cap - total))
            if not buf:
                break  # stdout EOF: not child failure; wait below
            total += len(buf)
            chunks.append(buf)
        if timed_out:
            # grab any bytes already buffered at the deadline (partial body accounting)
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            try:
                select.select([fd], [], [], 0.08)  # short real grace for late-arriving bytes
                while total < cap:
                    try:
                        buf = os.read(fd, min(65536, cap - total))
                    except (BlockingIOError, OSError):
                        break
                    if not buf:
                        break
                    total += len(buf)
                    chunks.append(buf)
            finally:
                fcntl.fcntl(fd, fcntl.F_SETFL, fl)
            _charge_partial(total, wal=_WAL_ACTIVE[0])  # preserve partial bytes on timeout
            raise ReadError("kubectl deadline exceeded")
        # EOF or cap reached: wait for the child to exit within the remaining deadline
        try:
            proc.wait(timeout=max(0.1, hard_deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            _charge_partial(total, wal=_WAL_ACTIVE[0])
            raise ReadError("kubectl did not exit after stdout EOF")
        if total >= cap:
            # cap reached before EOF: reject if the process produced more bytes than the cap
            # (a valid JSON prefix must not hide an over-cap suffix).
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            try:
                extra = os.read(fd, 1)
            finally:
                fcntl.fcntl(fd, fcntl.F_SETFL, fl)
            if extra:
                _charge_partial(total + len(extra), wal=_WAL_ACTIVE[0])
                raise ReadError("kubectl response exceeds cap")
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

def _check_gvr(doc, kind, api):
    """Exact GVR binding: the response must be the exact kind + apiVersion, not merely
    a member of the broad ALLOWED_API or a name ending in 'List'."""
    if not isinstance(doc, dict):
        return FAIL, "not an object"
    if doc.get("kind") != kind:
        return FAIL, "wrong resource kind"
    if doc.get("apiVersion") != api:
        return FAIL, "wrong apiVersion"
    return None


def _cond_ready(doc, ctype):
    conds = doc.get("status", {}).get("conditions", [])
    for c in conds:
        if isinstance(c, dict) and c.get("type") == ctype:
            return c.get("status")
    return None


def pred_hc_db(doc):
    err = _check_gvr(doc, "Cluster", "postgresql.cnpg.io/v1")
    if err:
        return err
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
    return INCONCLUSIVE, "DB condition indeterminate"


def pred_hc_arch(doc):
    err = _check_gvr(doc, "Cluster", "postgresql.cnpg.io/v1")
    if err:
        return err
    s = _cond_ready(doc, "ContinuousArchiving")
    if s == "True":
        return PASS, "ContinuousArchiving True"
    if s == "False":
        return FAIL, "ContinuousArchiving False"
    return INCONCLUSIVE, "ContinuousArchiving indeterminate"


def _ready_eps(doc):
    items = doc.get("items", [])
    ready = []
    for it in items:
        for ep in it.get("endpoints", []):
            if isinstance(ep, dict) and ep.get("conditions", {}).get("ready") is True:
                ready.append(ep)
    return ready, items


def pred_pr3(doc):
    err = _check_gvr(doc, "EndpointSliceList", "discovery.k8s.io/v1")
    if err:
        return err
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
    err = _check_gvr(doc, "ServiceList", "v1")
    if err:
        return err
    items = doc.get("items", [])
    if len(items) != 1:
        return FAIL if len(items) > 1 else INCONCLUSIVE, "service count != 1"
    svc = items[0]
    if not isinstance(svc, dict):
        return FAIL, "service not object"
    meta = svc.get("metadata", {})
    if not isinstance(meta, dict) or not meta.get("uid") or not meta.get("namespace"):
        return FAIL, "service identity missing"
    if meta.get("namespace") != "envoy-gateway-system":
        return FAIL, "service namespace not envoy-gateway-system"
    labels = meta.get("labels", {}) or {}
    if labels.get("gateway.envoyproxy.io/owning-gateway-name") != "portal-gateway" \
            or labels.get("gateway.envoyproxy.io/owning-gateway-namespace") != "portal":
        return FAIL, "service ownership labels missing"
    spec = svc.get("spec", {})
    if spec.get("type") != "LoadBalancer" or spec.get("externalTrafficPolicy") != "Local":
        return FAIL, "service type/policy wrong"
    ports = spec.get("ports", [])
    ok = any(p.get("port") == 443 and p.get("targetPort") in (10443, "10443") and p.get("protocol") == "TCP" for p in ports)
    if not ok:
        return FAIL, "443->10443 tuple missing"
    ingress = svc.get("status", {}).get("loadBalancer", {}).get("ingress", []) or []
    if not ingress or not any(i.get("ip") or i.get("hostname") for i in ingress if isinstance(i, dict)):
        return INCONCLUSIVE, "no LB IP/hostname identity"
    return PASS, "exact dataplane Service"


def pred_pr6(docs):
    # nine responses: policy lists empty; Tier/Felix compared to accepted safe baseline projection.
    if not isinstance(docs, list) or len(docs) != 9:
        return FAIL, "expected 9 responses"
    expected = [("NetworkPolicyList", "networking.k8s.io/v1"),
                ("NetworkPolicyList", "crd.projectcalico.org/v1"),
                ("GlobalNetworkPolicyList", "crd.projectcalico.org/v1"),
                ("HostEndpointList", "crd.projectcalico.org/v1"),
                ("ClusterNetworkPolicyList", "policy.networking.k8s.io/v1alpha2"),
                ("TierList", "crd.projectcalico.org/v1"),
                ("FelixConfigurationList", "crd.projectcalico.org/v1"),
                ("NamespaceList", "v1"),
                ("PodList", "v1")]
    for idx, (kind, api) in enumerate(expected):
        if not isinstance(docs[idx], dict) or docs[idx].get("kind") != kind or docs[idx].get("apiVersion") != api:
            return FAIL, "PR-6 response %d wrong kind/apiVersion" % idx
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
    if fspec.get("nftablesMode") != "Auto":
        return FAIL, "felix nftablesMode missing/drift"
    for k, v in fspec.items():
        if k == "nftablesMode":
            continue
        if v is not None:
            return FAIL, "felix field drift"
    # namespace list: typed items with full identity (no null/malformed)
    ns_items = docs[7].get("items", [])
    if not isinstance(ns_items, list):
        return FAIL, "namespace items not list"
    for n in ns_items:
        if not isinstance(n, dict):
            return FAIL, "namespace item malformed"
        nm = n.get("metadata", {})
        if not isinstance(nm, dict) or not nm.get("name") or not nm.get("uid"):
            return FAIL, "namespace item identity missing"
    # pod list: typed items + max_items (from readset, 200)
    pod_items = docs[8].get("items", [])
    if not isinstance(pod_items, list):
        return FAIL, "pod items not list"
    if len(pod_items) > 200:
        return FAIL, "pod list exceeds max_items"
    for p in pod_items:
        if not isinstance(p, dict):
            return FAIL, "pod item malformed"
        pm = p.get("metadata", {})
        if not isinstance(pm, dict) or not pm.get("name") or not pm.get("namespace") or not pm.get("uid"):
            return FAIL, "pod item identity missing"
    return PASS, "policy empty + tier/felix match accepted baseline"


def pred_hc_op(doc):
    err = _check_gvr(doc, "PodList", "v1")
    if err:
        return err
    pods = doc.get("items", [])
    if not isinstance(pods, list):
        return INCONCLUSIVE, "operator pods empty"
    if len(pods) > 200:
        return FAIL, "operator pods exceed max_items"
    if not pods:
        return INCONCLUSIVE, "operator pods empty"
    for p in pods:
        if not isinstance(p, dict):
            return FAIL, "operator pod malformed"
        if p.get("metadata", {}).get("deletionTimestamp"):
            return FAIL, "operator pod terminating"
        status = p.get("status")
        if not isinstance(status, dict):
            return FAIL, "operator pod status malformed"
        conds = {c.get("type"): c for c in status.get("conditions", []) if isinstance(c, dict)}
        if conds.get("Ready", {}).get("status") != "True":
            return FAIL, "operator pod not Ready"
    return PASS, "operator ready"


def pred_hc_dns(doc):
    err = _check_gvr(doc, "EndpointSliceList", "discovery.k8s.io/v1")
    if err:
        return err
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
    err = _check_gvr(doc, "Deployment", "apps/v1")
    if err:
        return err
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
    err = _check_gvr(doc, "Gateway", "gateway.networking.k8s.io/v1")
    if err:
        return err
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
        if p in _READ_CACHE:
            body = _READ_CACHE[p]
        else:
            _count_request()
            remaining = _remaining_body()
            if remaining <= 0:
                raise ReadError("overall body budget exhausted")
            remaining_secs = _remaining_seconds()
            if remaining_secs <= 0:
                raise ReadError("overall time budget exhausted")
            body, code = _io_call(run_kubectl_raw, kubectl, p, min(timeout, remaining_secs),
                                  min(cap, remaining))
            if len(body) > remaining:
                raise ReadError("overall body budget exceeded")
            _count_bytes(len(body))
            if code != 0:
                raise ReadError("kubectl exit %d" % code)
            _READ_CACHE[p] = body
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
    import threading

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            raise ReadError("redirect forbidden")

    def _read(opener, req):
        deadline = time.monotonic() + timeout
        chunks = []
        total = 0
        try:
            with opener.open(req, timeout=timeout) as resp:
                # expose the underlying socket so the total-deadline watchdog can terminate a
                # still-trickling body/framing read (inactivity timeout alone cannot).
                try:
                    raw = getattr(getattr(resp, "fp", None), "raw", None)
                    sock = getattr(raw, "_sock", None) if raw is not None else None
                    if sock is not None:
                        holder["sock"] = sock
                except Exception:
                    pass
                # read1 (a single recv) returns as soon as data is available, so a slow trickle is
                # re-checked against the absolute deadline between chunks instead of blocking until
                # a large amt or EOF; the underlying socket inactivity timeout is re-armed to the
                # remaining deadline so a fully stalled stream also aborts at the absolute deadline.
                read_fn = getattr(resp, "read1", None)
                if read_fn is None:
                    read_fn = resp.read
                while True:
                    remain = deadline - time.monotonic()
                    if remain <= 0:
                        raise ReadError("metrics deadline exceeded")
                    try:
                        raw = getattr(getattr(resp, "fp", None), "raw", None)
                        sock = getattr(raw, "_sock", None) if raw is not None else None
                        if sock is not None:
                            sock.settimeout(min(remain, 1.0))
                    except Exception:
                        pass
                    buf = read_fn(min(65536, cap + 1 - total))
                    # the blocking read may have completed after the absolute deadline
                    if time.monotonic() > deadline:
                        total += len(buf)  # count the late chunk before rejecting it
                        raise ReadError("metrics deadline exceeded")
                    if not buf:
                        break  # clean EOF before the deadline
                    total += len(buf)
                    if total > cap:
                        raise ReadError("metrics response exceeds cap")
                    chunks.append(buf)
                return b"".join(chunks)
        except ReadError:
            _charge_partial(total, wal=True)  # partial body consumed by overall AND WAL subset
            raise
        except Exception as e:
            _charge_partial(total, wal=True)  # partial body on transport error (never lose consumed bytes)
            raise ReadError("metrics fetch failed: %s" % type(e).__name__)

    opener = urllib.request.build_opener(NoRedirect, urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url)
    holder = {"body": None, "err": None, "done": False, "sock": None}

    def _worker():
        try:
            holder["body"] = _read(opener, req)
        except BaseException as e:
            holder["err"] = e
        finally:
            holder["done"] = True

    # the total deadline covers the WHOLE operation — connection open, status/headers, chunk
    # framing and body. A slow trickle during header/framing reads (which the socket inactivity
    # timeout cannot catch) is terminated by bounding the worker thread's completion; when the
    # underlying socket has already been exposed, it is closed so the worker finishes its byte
    # accounting before we return the terminal outcome.
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout)
    if not holder["done"]:
        sock = holder.get("sock")
        if sock is not None:
            # shutdown (not close) actually interrupts a blocked recv in the worker thread, so the
            # worker completes its durable byte accounting before we return the terminal outcome.
            import socket as _socket
            try:
                sock.shutdown(_socket.SHUT_RDWR)
            except Exception:
                try:
                    sock.close()
                except Exception:
                    pass
            t.join(1.0)
        raise ReadError("metrics deadline exceeded")
    if holder["err"] is not None:
        raise holder["err"]
    return holder["body"]


def run_wal_sample(kubectl, http_get, clock_evidence, gate):
    """5-request sample: Cluster -> Pod -> metrics -> same Pod -> same Cluster (30s hard deadline,
    2 MiB body cap; WAL-cumulative requests/bytes/seconds charged regardless of outcome)."""
    start = time.monotonic()
    body_total = [0]
    _WAL_SAMPLE_START[0] = start
    _WAL_ACTIVE[0] = True
    if _wal_exhausted():
        _WAL_SAMPLE_START[0] = None
        _WAL_ACTIVE[0] = False
        return INCONCLUSIVE, "WAL budget exhausted", None, None

    def raw(path):
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            raise ReadError("sample deadline exceeded")
        _count_request()
        _count_wal_request()
        # bound each metadata read by the minimum of sample/window/WAL/overall remaining body.
        remaining = min(_remaining_body(), _remaining_wal_body(), wal.SAMPLE_BODY_CAP - body_total[0])
        if remaining <= 0:
            raise ReadError("body budget exhausted")
        t_limit = max(0.0, min(wal.REQ_TIMEOUT, _remaining_seconds(), _remaining_wal_seconds(),
                               wal.SAMPLE_DEADLINE - (time.monotonic() - start)))
        if t_limit <= 0:
            raise ReadError("time budget exhausted")
        body, code = _io_call(run_kubectl_raw, kubectl, path, t_limit, min(wal.METADATA_CAP, remaining))
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            raise ReadError("sample deadline exceeded")
        body_total[0] += len(body)
        if body_total[0] > wal.SAMPLE_BODY_CAP:
            raise ReadError("sample body cap exceeded")
        if len(body) > remaining:
            raise ReadError("overall body budget exceeded")
        _count_bytes(len(body))
        _count_wal_bytes(len(body))
        if code != 0:
            raise ReadError("kubectl exit %d" % code)
        return validate_envelope(body, False)

    try:
        cluster_path = "/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db"
        cluster = raw(cluster_path)
        primary = cluster.get("status", {}).get("currentPrimary")
        if not primary:
            return INCONCLUSIVE, "no currentPrimary", None, None
        if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", str(primary)):
            return INCONCLUSIVE, "invalid primary name", None, None
        pod_path = "/api/v1/namespaces/portal/pods/" + str(primary)
        pod = raw(pod_path)
        pod_ip = pod.get("status", {}).get("podIP")
        if not pod_ip:
            return INCONCLUSIVE, "pod IP missing", None, None
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            return INCONCLUSIVE, "sample deadline exceeded", None, None
        try:
            _count_request()
            _count_wal_request()
            remaining = min(_remaining_body(), _remaining_wal_body(), wal.SAMPLE_BODY_CAP - body_total[0])
            if remaining <= 0:
                return INCONCLUSIVE, "body budget exhausted", None, None
            t_limit = max(0.0, min(wal.REQ_TIMEOUT, _remaining_seconds(), _remaining_wal_seconds(),
                                   wal.SAMPLE_DEADLINE - (time.monotonic() - start)))
            if t_limit <= 0:
                return INCONCLUSIVE, "time budget exhausted", None, None
            raw_metrics = _io_call(http_get, "http://%s:9187/metrics" % pod_ip, t_limit,
                                   min(wal.METRIC_CAP, remaining))
        except ReadError as e:
            return INCONCLUSIVE, str(e), None, None
        # account the raw received bytes BEFORE decode and before any terminal outcome; a decode
        # failure or a later accounting error must not lose the bytes already received.
        body_total[0] += len(raw_metrics)
        if body_total[0] > wal.SAMPLE_BODY_CAP:
            _charge_partial(len(raw_metrics), wal=True)
            return INCONCLUSIVE, "sample body cap exceeded", None, None
        _charge_partial(len(raw_metrics), wal=True)
        try:
            metrics_text = raw_metrics.decode()
        except UnicodeDecodeError:
            return INCONCLUSIVE, "metrics not valid UTF-8", None, None
        if time.monotonic() - start > wal.SAMPLE_DEADLINE:
            return INCONCLUSIVE, "sample deadline exceeded", None, None
        pod_after = raw(pod_path)
        cluster_after = raw(cluster_path)
        disp, m, detail = wal.wal_sample(cluster, pod, metrics_text, cluster_after, pod_after,
                                         clock_evidence, baseline=gate.get("wal_baseline"),
                                         op_end_utc=gate.get("operation_end_utc"),
                                         gate_hash=gate_identity_sha256(gate),
                                         baseline_observed_at=gate.get("baseline_observed_at"))
        return disp, detail, m, pod.get("metadata", {}).get("uid")
    except ReadError as e:
        return INCONCLUSIVE, str(e), None, None
    finally:
        _count_wal_seconds(time.monotonic() - start)
        _WAL_SAMPLE_START[0] = None
        _WAL_ACTIVE[0] = False


def run_wal_window(kubectl, http_get, gate, state_dir, clock_evidence, stage="S0"):
    """WAL observation window: <=3 samples at absolute offsets 0/300/600s; 660s hard deadline and
    6 MiB window body cap; baseline persists across slots."""
    if stage != "S0":
        op_end = gate.get("operation_end_utc")
        if isinstance(op_end, bool) or not isinstance(op_end, (int, float)):
            return INCONCLUSIVE, "no operation boundary for post-operation stage"
        issued_epoch = parse_utc(gate.get("issued_at_utc", "")) if gate.get("issued_at_utc") else None
        if issued_epoch is not None and op_end < issued_epoch:
            return INCONCLUSIVE, "operation boundary not bound to gate (before issued_at)"
        # operation boundary must be bound to a verified action receipt that confirms the
        # specific gate/stage/operation/successful-outcome, not just three equal fields.
        receipt = gate.get("action_receipt")
        prev_stage = STAGES[STAGES.index(stage) - 1]
        if not isinstance(receipt, dict) \
                or receipt.get("source_sha") != gate.get("source_sha") \
                or receipt.get("package_sha256") != gate.get("package_sha256") \
                or receipt.get("gate_sha256") != gate_identity_sha256(gate) \
                or receipt.get("stage") != prev_stage \
                or receipt.get("outcome") != PASS \
                or receipt.get("operation_end_utc") != op_end:
            return INCONCLUSIVE, "operation boundary not bound to an action receipt"
    baseline_rec = read_wal_baseline_record(state_dir, gate)
    baseline = gate.get("wal_baseline") or (baseline_rec.get("metrics") if baseline_rec else None)
    baseline_pod_uid = baseline_rec.get("pod_uid") if baseline_rec else None
    baseline_observed_at = baseline_rec.get("observed_at") if baseline_rec else None
    window_start = time.monotonic()
    wal_bytes_start = _WAL_TRANSPORT["bytes"]
    slot_start = window_start
    for slot in range(wal.WINDOW_SLOTS):
        if time.monotonic() - window_start > wal.WINDOW_DEADLINE:
            return INCONCLUSIVE, "window deadline exceeded"
        if slot > 0:
            elapsed = time.monotonic() - slot_start
            sleep_time = max(0.0, 300.0 - elapsed)
            # the wait is a first-class permit: bounded by BOTH overall and WAL remaining time
            remaining = min(_remaining_seconds(), _remaining_wal_seconds())
            if remaining <= 0:
                return INCONCLUSIVE, "time budget exhausted"
            if sleep_time > remaining:
                sleep_time = remaining
            time.sleep(sleep_time)
            _count_wal_seconds(sleep_time)  # WAL elapsed includes slot waits (durable)
            _count_seconds(sleep_time)  # overall elapsed tracked during execution
            slot_start = time.monotonic()
        wgate = dict(gate)
        if baseline is not None:
            wgate["wal_baseline"] = baseline
        if baseline_observed_at is not None:
            wgate["baseline_observed_at"] = baseline_observed_at
        if baseline_pod_uid is not None:
            wgate["baseline_pod_uid"] = baseline_pod_uid
        res = run_wal_sample(kubectl, http_get, clock_evidence, wgate)
        if isinstance(res, tuple) and len(res) >= 3:
            disp, detail, m = res[0], res[1], res[2]
            pod_uid = res[3] if len(res) > 3 else None
        else:
            disp, detail, m, pod_uid = res[0], res[1], None, None
        if _WAL_TRANSPORT["bytes"] - wal_bytes_start > wal.WINDOW_BODY_CAP:
            return INCONCLUSIVE, "window body cap exceeded"
        # baseline observation identity: the pod UID must be stable across samples
        if baseline_pod_uid is not None and pod_uid is not None and pod_uid != baseline_pod_uid:
            return INCONCLUSIVE, "baseline observation identity changed (pod UID)"
        if m is not None and disp != FAIL:
            persist_wal_baseline(state_dir, gate, m, pod_uid=pod_uid, observed_at=time.time())
            baseline = m
            baseline_pod_uid = pod_uid
            baseline_observed_at = time.time()
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
        budget = read_budget(gate, args.state_dir)
    except ReadError as e:
        print("STOP: " + str(e), file=sys.stderr)
        return 2
    if not budget_valid(budget):
        print("STOP: budget state not finite/nonnegative (corrupt)", file=sys.stderr)
        return 2
    if budget_exhausted(budget):
        print("STOP: budget exhausted", file=sys.stderr)
        return 2
    _set_budget_base(budget)
    _set_budget_context(gate, args.state_dir, budget)
    _reset_transport()
    _reset_read_cache()
    read_ids = list(readset["reads"].keys())
    wal_id = "HC-WAL-PROGRESS" if "HC-WAL-PROGRESS" in readset["reads"] else None
    ordered = ([wal_id] + [r for r in read_ids if r != wal_id]) if wal_id else read_ids
    first_obs = {}
    for read_id in ordered:
        spec = readset["reads"][read_id]
        if args.stage not in spec["stages"]:
            journal["reads"][read_id] = {"disposition": NOT_APPLICABLE}
            continue
        start = time.monotonic()
        if read_id.startswith("HC-") and read_id != wal_id:
            first_obs[read_id] = start
        try:
            if spec.get("method") == "wal":
                disp, detail = run_wal_window(args.kubectl, default_http_get, gate, args.state_dir, gate.get("clock_evidence"), args.stage)
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

    # bounded health windows (per-check W/I/N) + freshness re-check at verdict.
    health_ids = [r for r in ordered
                  if r != wal_id and r.startswith("HC-") and args.stage in readset["reads"][r]["stages"]]
    # per-check W/I/N: W = absolute window (s), I = retry interval (s), N = TOTAL observations
    # INCLUDING the first GET (already done in the main loop) and the final freshness re-read.
    # retries = N - 2.
    HEALTH_WINDOWS = {
        "HC-DB": {"window": 60, "interval": 10, "n": 6},
        "HC-ARCH-STATE": {"window": 60, "interval": 10, "n": 6},  # shares the DB GET within a round
        "HC-OP": {"window": 60, "interval": 10, "n": 6},
        "HC-DNS": {"window": 30, "interval": 5, "n": 6},
        "HC-PORTAL": {"window": 60, "interval": 10, "n": 6},
        "HC-GW": {"window": 120, "interval": 10, "n": 12},
    }
    HEALTH_MAX_AGE = {"HC-GW": 60.0}  # Gateway freshness <= 60s; others default 30s
    max_retries = max(w["n"] - 2 for w in HEALTH_WINDOWS.values())
    for round_no in range(1, max_retries + 1):
        _reset_read_cache()  # each round is a fresh GET (no cache hit across rounds)
        progressed = False
        for read_id in health_ids:
            cur = journal["reads"].get(read_id, {}).get("disposition")
            if cur == FAIL or cur == PASS:
                continue  # failure precedence / already resolved
            win = HEALTH_WINDOWS.get(read_id, {"window": 60, "interval": 10, "n": 6})
            if round_no > win["n"] - 2:
                continue  # N total observations, minus first GET and the final freshness re-read
            fo = first_obs.get(read_id, time.monotonic())
            # absolute window end is anchored to this check's FIRST observation, not a shared clock
            if time.monotonic() - fo >= win["window"]:
                continue  # window already ended before this retry
            sleep_time = min(win["interval"], max(0.0, _remaining_seconds()))
            if sleep_time > 0:
                time.sleep(sleep_time)
                _count_seconds(sleep_time)
            # after the sleep the window may have ended (the sleep crossed the absolute end)
            if time.monotonic() - fo >= win["window"]:
                journal["reads"][read_id] = {"disposition": FAIL, "detail": "health window expired before observation",
                                             "attempt": round_no + 1, "observed_mono": time.monotonic()}
                progressed = True
                continue
            window_remaining = win["window"] - (time.monotonic() - fo)
            try:
                expect_list, pred = PREDICATES[read_id]
                doc = run_read(readset, read_id, args.kubectl, min(15, max(0.1, window_remaining)))
                disp, detail = pred(doc)
                # the observation may have completed after the window end (a late response)
                if time.monotonic() - fo >= win["window"]:
                    journal["reads"][read_id] = {"disposition": FAIL, "detail": "health observation after window end",
                                                 "attempt": round_no + 1, "observed_mono": time.monotonic()}
                else:
                    journal["reads"][read_id] = {"disposition": disp, "detail": detail,
                                                 "attempt": round_no + 1, "observed_mono": time.monotonic()}
            except ReadError as e:
                journal["reads"][read_id] = {"disposition": INCONCLUSIVE, "error": str(e),
                                             "attempt": round_no + 1, "observed_mono": time.monotonic()}
            progressed = True
        if not progressed:
            break
    # freshness re-read (the final N-th observation): reverse order so the shared DB/ARCH
    # observation is the freshest); a FAIL is never erased by this sweep.
    _reset_read_cache()
    for read_id in reversed(health_ids):
        cur = journal["reads"].get(read_id, {}).get("disposition")
        if cur == FAIL:
            continue  # failure precedence
        win = HEALTH_WINDOWS.get(read_id, {"window": 60, "interval": 10, "n": 6})
        fo = first_obs.get(read_id, time.monotonic())
        window_remaining = win["window"] - (time.monotonic() - fo)
        # a late healthy response must not close a check that never passed inside its window
        if cur == INCONCLUSIVE and window_remaining <= 0:
            journal["reads"][read_id] = {"disposition": FAIL, "detail": "health window expired without PASS",
                                         "observed_mono": time.monotonic()}
            continue
        timeout = min(15, max(0.1, window_remaining)) if cur == INCONCLUSIVE else 15
        try:
            expect_list, pred = PREDICATES[read_id]
            doc = run_read(readset, read_id, args.kubectl, timeout)
            disp, detail = pred(doc)
            if cur == INCONCLUSIVE and time.monotonic() - fo >= win["window"]:
                journal["reads"][read_id] = {"disposition": FAIL, "detail": "health observation after window end",
                                             "attempt": journal["reads"][read_id].get("attempt", 1) + 1,
                                             "observed_mono": time.monotonic()}
            else:
                journal["reads"][read_id] = {"disposition": disp, "detail": detail,
                                             "attempt": journal["reads"][read_id].get("attempt", 1) + 1,
                                             "observed_mono": time.monotonic()}
        except ReadError as e:
            journal["reads"][read_id] = {"disposition": INCONCLUSIVE, "error": str(e),
                                         "observed_mono": time.monotonic()}
    # freshness gate: stale mandatory observation -> FAIL (no PASS with stale health). Per-check age.
    now_mono = time.monotonic()
    for read_id in health_ids:
        ent = journal["reads"].get(read_id, {})
        obs = ent.get("observed_mono")
        max_age = HEALTH_MAX_AGE.get(read_id, 30.0)
        if obs is not None and now_mono - obs > max_age:
            journal["reads"][read_id] = {"disposition": FAIL, "detail": "health observation stale at verdict"}

    # authoritative budget: re-read the on-disk authority (atomic deltas already persisted by
    # _charge). Seconds are the accumulated _count_seconds/_count_wal charges, not the (sweep-
    # overwritten) per-read duration_ms of the final journal.
    budget = read_budget(gate)
    _set_budget_context(None, None, None)  # clear context; direct run_wal_sample calls must not see a stale budget
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
