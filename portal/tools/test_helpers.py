#!/usr/bin/env python3
"""Synthetic mock tests for the Owner provisioning helpers (R2-01).

No real kubectl, no real credentials. Verifies: password format validation,
and the fail-closed create-only flow (Forbidden/network precheck -> STOP before
any write; existing Secret -> STOP; success -> atomic create only).
"""
import importlib.util
import unittest
from unittest import mock


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ui = load("portal/tools/provision-ui-auth.py", "ui_auth")


class _TtyStdin:
    def isatty(self):
        return True


class _FakeProc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestValidatePassword(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(ui.validate_password("A" * 43), "")

    def test_wrong_length(self):
        self.assertIn("exactly", ui.validate_password("short"))

    def test_bad_alphabet(self):
        self.assertIn("base64url", ui.validate_password("a" * 42 + "+"))


class TestFailClosedCreateOnly(unittest.TestCase):
    def _run(self, probe_result, create_result=None):
        calls = {"create": 0, "verbs": []}

        def fake_kubectl(args, input_text=None):
            if args[0] == "kubectl":
                if "get" in args:
                    calls["verbs"].append("get")
                    return probe_result
                if "create" in args:
                    calls["verbs"].append("create")
                    calls["create"] += 1
                    return create_result
            raise AssertionError(f"unexpected args: {args}")

        with mock.patch.object(ui, "run_kubectl", side_effect=fake_kubectl), \
             mock.patch.object(ui.sys, "argv", ["provision-ui-auth.py", "--context", "test-context"]), \
             mock.patch.object(ui.sys, "stdin", _TtyStdin()), \
             mock.patch.object(ui.getpass, "getpass", side_effect=["A" * 43, "A" * 43]):
            code = ui.main()
        return code, calls

    def test_forbidden_probe_stops_before_write(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=1))
        self.assertEqual(code, 4)
        self.assertEqual(calls["create"], 0)
        self.assertEqual(calls["verbs"], ["get"])

    def test_existing_secret_stops(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=0, stdout="secret/portal-ui-auth\n"))
        self.assertEqual(code, 3)
        self.assertEqual(calls["create"], 0)

    def test_success_uses_create_only(self):
        code, calls = self._run(
            probe_result=_FakeProc(returncode=0, stdout=""),
            create_result=_FakeProc(returncode=0),
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls["create"], 1)
        self.assertEqual(calls["verbs"], ["get", "create"])

    def test_already_exists_race_stops_no_overwrite(self):
        code, calls = self._run(
            probe_result=_FakeProc(returncode=0, stdout=""),
            create_result=_FakeProc(returncode=1),
        )
        self.assertEqual(code, 4)
        self.assertEqual(calls["create"], 1)
        for forbidden in ("apply", "patch", "replace"):
            self.assertNotIn(forbidden, calls["verbs"])


if __name__ == "__main__":
    unittest.main()
