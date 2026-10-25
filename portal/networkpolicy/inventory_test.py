#!/usr/bin/env python3
"""Offline mock tests for inventory.py safe projection + error classification.

No kubectl, no cluster. Verifies the collector projects away secret-bearing
fields (managedFields, annotations) and classifies errors into safe categories
(TIMEOUT / FORBIDDEN / API_NOT_SERVED / CONNECTION / GET_FAILED) instead of
leaking tracebacks or credentials.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HERE = os.path.dirname(os.path.abspath(__file__))
inv = load(os.path.join(HERE, "inventory.py"), "inventory")


class TestProjection(unittest.TestCase):
    def test_strips_managed_fields_and_annotations(self):
        obj = {
            "metadata": {
                "name": "x",
                "namespace": "portal",
                "labels": {"a": "b"},
                "annotations": {
                    "kubectl.kubernetes.io/last-applied-configuration": '{"data":{"password":"SECRET"}}'
                },
                "managedFields": [{"manager": "kubectl"}],
            },
            "spec": {"podSelector": {"matchLabels": {"app": "portal"}}},
            "items": [{"metadata": {"annotations": {"x": "y"}, "managedFields": [{}]}, "spec": {}}],
        }
        out = inv.project(obj)
        self.assertNotIn("managedFields", out["metadata"])
        self.assertNotIn("annotations", out["metadata"])
        self.assertNotIn("managedFields", out["items"][0]["metadata"])
        self.assertNotIn("annotations", out["items"][0]["metadata"])
        # name/labels/spec retained
        self.assertEqual(out["metadata"]["name"], "x")
        self.assertEqual(out["spec"]["podSelector"]["matchLabels"]["app"], "portal")
        # no secret leaks through
        self.assertNotIn("SECRET", json.dumps(out))


class TestClassify(unittest.TestCase):
    def test_timeout(self):
        self.assertEqual(inv.classify(None, "", True), "TIMEOUT")

    def test_forbidden(self):
        self.assertEqual(inv.classify(1, "Error from server (Forbidden): ...", False), "FORBIDDEN")

    def test_api_not_served(self):
        self.assertEqual(inv.classify(1, 'error: the server could not find the requested resource', False), "API_NOT_SERVED")

    def test_connection(self):
        self.assertEqual(inv.classify(1, "The connection to the server ... was refused", False), "CONNECTION")

    def test_generic_failure(self):
        self.assertEqual(inv.classify(1, "something else", False), "GET_FAILED")

    def test_success_is_none(self):
        self.assertIsNone(inv.classify(0, "", False))


class _FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestMain(unittest.TestCase):
    def _run(self, results, which=True):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "inv")
        calls = {"argv": []}
        with mock.patch.object(shutil, "which", return_value="/usr/bin/kubectl" if which else None), \
             mock.patch.object(subprocess, "run", side_effect=lambda argv, **kw: results.pop(0)) as r, \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "ctx", "--output", outdir]):
            code = inv.main()
        return code, outdir

    def test_all_success_writes_jsonl_exit0(self):
        results = [_FakeResult(0, json.dumps({"items": []}), "") for _ in inv.COMMANDS]
        code, outdir = self._run(results)
        self.assertEqual(code, 0)
        with open(os.path.join(outdir, "inventory.jsonl")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), len(inv.COMMANDS))
        for ln in lines:
            r = json.loads(ln)
            self.assertEqual(r["category"], None)

    def test_failure_exit1(self):
        results = []
        for i, _ in enumerate(inv.COMMANDS):
            if i == 0:
                results.append(_FakeResult(1, "", "Error from server (Forbidden)"))
            else:
                results.append(_FakeResult(0, json.dumps({"items": []}), ""))
        code, _ = self._run(results)
        self.assertEqual(code, 1)

    def test_full_object_projection_on_write(self):
        # One full-object command returns JSON with annotations; ensure projection.
        payload = json.dumps({"items": [{"metadata": {"name": "g", "annotations": {"secret": "x"}, "managedFields": [{}]}, "spec": {}}]})
        results = []
        for cmd in inv.COMMANDS:
            if cmd in inv.FULL_OBJECT_KINDS:
                results.append(_FakeResult(0, payload, ""))
            else:
                results.append(_FakeResult(0, "", ""))
        code, outdir = self._run(results)
        self.assertEqual(code, 0)
        with open(os.path.join(outdir, "inventory.jsonl")) as f:
            for ln in f:
                r = json.loads(ln)
                if '"annotations"' not in r["output"]:
                    continue
                self.fail("annotations leaked into projected output")

    def test_no_kubectl_blocks(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "novel-output")
        with mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "c", "--output", outdir]):
            with self.assertRaises(SystemExit) as cm:
                inv.main()
        self.assertIn("BLOCKED", str(cm.exception))
        self.assertFalse(os.path.exists(outdir), "no output dir should be created when kubectl is absent")


if __name__ == "__main__":
    unittest.main()
