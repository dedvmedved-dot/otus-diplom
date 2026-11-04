#!/usr/bin/env python3
"""Offline tests for the readiness wrapper (no live cluster/SSH).

Injected transport is a fake kubectl script; injected clock covers gate expiry.
These tests prove branching/bounds, not cryptographic or network truth.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import wrapper  # noqa: E402


def fake_kubectl(rows):
    """Write a fake kubectl that echoes the given raw JSON for any path."""
    d = tempfile.mkdtemp()
    path = os.path.join(d, "kubectl")
    with open(path, "w") as f:
        f.write("#!/bin/sh\ncat %s\n" % json.dumps(rows))
    os.chmod(path, 0o755)
    return path


def gate(source_sha="a" * 40, mode="LIVE", issued="2026-11-04T00:00:00Z", expiry=24, consumed=False, ctx=wrapper.CONTEXT):
    return {"source_sha": source_sha, "mode": mode, "issued_at_utc": issued, "expiry_hours": expiry, "run_budget_consumed": consumed, "context": ctx}


def issued_epoch():
    import calendar
    return calendar.timegm((2026, 11, 4, 0, 0, 0))


class TestGateValidation(unittest.TestCase):
    def test_valid(self):
        ok, err = wrapper.validate_gate(gate(), now=issued_epoch() + 60)
        self.assertTrue(ok, err)

    def test_expired(self):
        ok, err = wrapper.validate_gate(gate(), now=issued_epoch() + 25 * 3600)
        self.assertFalse(ok)

    def test_test_only_rejected(self):
        ok, _ = wrapper.validate_gate(gate(mode="TEST_ONLY"), now=issued_epoch() + 60)
        self.assertFalse(ok)

    def test_bad_source(self):
        ok, _ = wrapper.validate_gate(gate(source_sha="zzz"), now=issued_epoch() + 60)
        self.assertFalse(ok)

    def test_budget_consumed(self):
        ok, _ = wrapper.validate_gate(gate(consumed=True), now=issued_epoch() + 60)
        self.assertFalse(ok)

    def test_wrong_context(self):
        ok, _ = wrapper.validate_gate(gate(ctx="other-context"), now=issued_epoch() + 60)
        self.assertFalse(ok)


class TestEnvelope(unittest.TestCase):
    def test_list_ok(self):
        wrapper.validate_envelope(b'{"apiVersion":"v1","kind":"PodList","items":[]}')

    def test_continue_rejected(self):
        with self.assertRaises(wrapper.ReadError):
            wrapper.validate_envelope(b'{"apiVersion":"v1","kind":"PodList","items":[],"metadata":{"continue":"x"}}')

    def test_malformed(self):
        with self.assertRaises(wrapper.ReadError):
            wrapper.validate_envelope(b"not json")


class TestReadSet(unittest.TestCase):
    def test_readset_wellformed(self):
        rs = wrapper.load_readset()
        for rid, spec in rs["reads"].items():
            self.assertIn("stages", spec)
            if spec.get("method") == "kubectl":
                self.assertTrue("path" in spec or "paths" in spec)

    def test_path_rejection(self):
        with self.assertRaises(wrapper.ReadError):
            wrapper.run_kubectl_raw("/bin/false", "/bad path; rm -rf", 5, 1024)


class TestWrapperMain(unittest.TestCase):
    def test_no_overwrite(self):
        d = tempfile.mkdtemp()
        out = os.path.join(d, "j.json")
        open(out, "w").write("{}")
        rc = wrapper.main(["--gate", __file__, "--out", out, "--stage", "S0", "--now", "1730678400"])
        self.assertEqual(rc, 2)

    def test_gate_rejected_zero_requests(self):
        d = tempfile.mkdtemp()
        g = os.path.join(d, "g.json")
        json.dump(gate(mode="TEST_ONLY"), open(g, "w"))
        rc = wrapper.main(["--gate", g, "--out", os.path.join(d, "j.json"), "--stage", "S0", "--now", "1730678400"])
        self.assertEqual(rc, 2)
        self.assertFalse(os.path.exists(os.path.join(d, "j.json")))

    def test_successful_run_fail_closed(self):
        d = tempfile.mkdtemp()
        g = os.path.join(d, "g.json")
        json.dump(gate(), open(g, "w"))
        rows = '{"apiVersion":"v1","kind":"PodList","items":[]}'
        rc = wrapper.main(["--gate", g, "--out", os.path.join(d, "j.json"), "--stage", "S0",
                           "--kubectl", fake_kubectl(rows), "--now", "1730678400"])
        self.assertEqual(rc, 0)
        j = json.load(open(os.path.join(d, "j.json")))
        self.assertIn(j["aggregate"], (wrapper.PASS, wrapper.INCONCLUSIVE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
