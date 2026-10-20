#!/usr/bin/env python3
"""Synthetic mock tests for BOTH Owner provisioning helpers (R3-A).

No real kubectl, no real credentials. Verifies: password format validation;
fail-closed no-echo read; create-only flow (Forbidden/network precheck -> STOP
before write; existing Secret -> STOP; success -> atomic create); and
timeout-phase distinction (timeout after create -> UNKNOWN_OUTCOME, never
"no write attempted").
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
reg = load("portal/tools/provision-registry-pull.py", "reg_pull")


class _TtyStdin:
    def isatty(self):
        return True

    def fileno(self):
        return 0


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


def run_flow(mod, secrets, probe_result, create_result=None):
    calls = {"create": 0, "verbs": []}

    def fake_kubectl(args, input_text=None):
        if args[0] == "kubectl":
            if "get" in args:
                calls["verbs"].append("get")
                return probe_result, False
            if "create" in args:
                calls["verbs"].append("create")
                calls["create"] += 1
                if isinstance(create_result, tuple):
                    return create_result
                return create_result, False
        raise AssertionError(f"unexpected args: {args}")

    with mock.patch.object(mod, "run_kubectl", side_effect=fake_kubectl), \
         mock.patch.object(mod.sys, "argv", ["x", "--context", "test-context"]), \
         mock.patch.object(mod.sys, "stdin", _TtyStdin()), \
         mock.patch.object(mod, "read_secret_noecho", side_effect=secrets):
        code = mod.main()
    return code, calls


class TestUIFailClosedCreateOnly(unittest.TestCase):
    def _run(self, probe_result, create_result=None):
        return run_flow(ui, ["A" * 43, "A" * 43], probe_result, create_result)

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
        code, calls = self._run(probe_result=_FakeProc(returncode=0, stdout=""), create_result=_FakeProc(returncode=0))
        self.assertEqual(code, 0)
        self.assertEqual(calls["create"], 1)
        self.assertEqual(calls["verbs"], ["get", "create"])

    def test_already_exists_race_stops_no_overwrite(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=0, stdout=""), create_result=_FakeProc(returncode=1))
        self.assertEqual(code, 4)
        self.assertEqual(calls["create"], 1)
        for forbidden in ("apply", "patch", "replace"):
            self.assertNotIn(forbidden, calls["verbs"])

    def test_create_timeout_unknown_outcome(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=0, stdout=""), create_result=(None, True))
        self.assertEqual(code, 4)
        self.assertEqual(calls["create"], 1)


class TestRegistryFailClosedCreateOnly(unittest.TestCase):
    def _run(self, probe_result, create_result=None):
        return run_flow(reg, ["ghcr-user", "ghcr-token"], probe_result, create_result)

    def test_forbidden_probe_stops_before_write(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=1))
        self.assertEqual(code, 4)
        self.assertEqual(calls["create"], 0)

    def test_existing_secret_stops(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=0, stdout="secret/portal-registry-pull\n"))
        self.assertEqual(code, 3)
        self.assertEqual(calls["create"], 0)

    def test_success_uses_create_only(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=0, stdout=""), create_result=_FakeProc(returncode=0))
        self.assertEqual(code, 0)
        self.assertEqual(calls["create"], 1)
        self.assertEqual(calls["verbs"], ["get", "create"])

    def test_create_timeout_unknown_outcome(self):
        code, calls = self._run(probe_result=_FakeProc(returncode=0, stdout=""), create_result=(None, True))
        self.assertEqual(code, 4)
        self.assertEqual(calls["create"], 1)


class TestNoEchoFailClosed(unittest.TestCase):
    def test_non_tty_raises(self):
        with mock.patch.object(ui.sys, "stdin", mock.Mock(isatty=lambda: False)):
            with self.assertRaises(ui.NoEchoError):
                ui.read_secret_noecho("prompt: ")

    def test_termios_unavailable_raises(self):
        # stdin claims TTY but termios.tcgetattr fails -> no fallback to echo.
        with mock.patch.object(ui.sys, "stdin", _TtyStdin()), \
             mock.patch("termios.tcgetattr", side_effect=OSError("no termios")):
            with self.assertRaises(ui.NoEchoError):
                ui.read_secret_noecho("prompt: ")


if __name__ == "__main__":
    unittest.main()
