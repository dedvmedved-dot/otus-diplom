#!/usr/bin/env python3
"""Synthetic mock tests for BOTH Owner provisioning helpers (R3-A).

No real kubectl, no real credentials. Verifies: password format validation;
fail-closed no-echo read; create-only flow (Forbidden/network precheck -> STOP
before write; existing Secret -> STOP; success -> atomic create); and
timeout-phase distinction (timeout after create -> UNKNOWN_OUTCOME, never
"no write attempted").
"""
import importlib.util
import os
import io
import json
import base64
import hashlib
import subprocess
import contextlib
import unittest
from unittest import mock


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Resolve helpers relative to THIS file (cwd-independent), so the suite works
# from repo root AND from portal/ (the workflow's working-directory).
_HERE = os.path.dirname(os.path.abspath(__file__))
ui = load(os.path.join(_HERE, "provision-ui-auth.py"), "ui_auth")
reg = load(os.path.join(_HERE, "provision-registry-pull.py"), "reg_pull")


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


class TestRealInputAndSubprocessFlow(unittest.TestCase):
    def test_input_cancel_and_restore_both_helpers(self):
        for mod in (ui, reg):
            for text in ("", "fake\x03", "fake\x04", "fake", "fake\n"):
                with self.subTest(helper=mod.SECRET_NAME, input=repr(text)):
                    stdin = io.StringIO(text)
                    stdin.isatty = lambda: True
                    stdin.fileno = lambda: 0
                    with mock.patch.object(mod.sys, "stdin", stdin), \
                         mock.patch("termios.tcgetattr", return_value=[1, 2, 3]), \
                         mock.patch("tty.setraw") as raw, \
                         mock.patch("termios.tcsetattr") as restore, \
                         contextlib.redirect_stderr(io.StringIO()) as output:
                        if text.endswith("\n"):
                            self.assertEqual(mod.read_secret_noecho("prompt"), "fake")
                        else:
                            with self.assertRaises(mod.NoEchoError):
                                mod.read_secret_noecho("prompt")
                        raw.assert_called_once()
                        restore.assert_called_once()
                        self.assertNotIn("fake", output.getvalue())

    def test_terminal_setup_restore_and_encoding_fail_closed(self):
        for mod in (ui, reg):
            for stage in ('setup', 'restore', 'read'):
                stdin = io.StringIO('synthetic\n')
                stdin.isatty = lambda: True
                stdin.fileno = lambda: 0
                if stage == 'read': stdin.read = mock.Mock(side_effect=UnicodeError('synthetic'))
                with self.subTest(helper=mod.SECRET_NAME, stage=stage), \
                     mock.patch.object(mod.sys, 'stdin', stdin), \
                     mock.patch('termios.tcgetattr', return_value=[1, 2, 3]), \
                     mock.patch('tty.setraw', side_effect=OSError('synthetic') if stage == 'setup' else None), \
                     mock.patch('termios.tcsetattr', side_effect=OSError('synthetic') if stage == 'restore' else None) as restore, \
                     contextlib.redirect_stderr(io.StringIO()) as output:
                    with self.assertRaises(mod.NoEchoError): mod.read_secret_noecho('prompt')
                    restore.assert_called_once()
                    self.assertNotIn('synthetic', output.getvalue())

    def test_input_failure_prevents_every_subprocess(self):
        for mod in (ui, reg):
            for failure in (mod.NoEchoError("input cancelled"), mod.NoEchoError("no echo")):
                with mock.patch.object(mod.sys, "argv", ["helper", "--context", "test"]), \
                     mock.patch.object(mod.sys, "stdin", _TtyStdin()), \
                     mock.patch.object(mod, "read_secret_noecho", side_effect=failure), \
                     mock.patch.object(mod.subprocess, "run") as run, \
                     contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(mod.main(), 2)
                    run.assert_not_called()

    def test_subprocess_phases_and_non_disclosure(self):
        password, token = "Q" * 43, "synthetic-registry-token"
        verifier = hashlib.sha256(password.encode()).hexdigest()
        for mod in (ui, reg):
            for outcome in ("success", "exists", "probe-denied", "probe-timeout", "missing", "create-denied", "race", "create-timeout"):
                with self.subTest(helper=mod.SECRET_NAME, outcome=outcome):
                    calls = []
                    def subprocess_run(args, **kwargs):
                        calls.append((args, kwargs))
                        self.assertNotIn("env", kwargs)
                        for secret in (password, token, verifier):
                            self.assertNotIn(secret, " ".join(args))
                        self.assertEqual(kwargs["timeout"], mod.KUBECTL_TIMEOUT)
                        if "get" in args:
                            self.assertIsNone(kwargs["input"])
                            if outcome == "missing": raise FileNotFoundError("synthetic")
                            if outcome == "probe-timeout": raise subprocess.TimeoutExpired(args, 60)
                            return _FakeProc(1 if outcome == "probe-denied" else 0, "secret/existing" if outcome == "exists" else "")
                        self.assertIn("create", args)
                        self.assertNotIn("apply", args)
                        body = json.loads(kwargs["input"])
                        self.assertEqual(body["metadata"], {"name": mod.SECRET_NAME, "namespace": "portal"})
                        self.assertEqual(set(body), {"apiVersion", "kind", "metadata", "type", "data"})
                        if mod is ui:
                            self.assertEqual(base64.b64decode(body["data"]["password-sha256"]).decode(), verifier)
                            self.assertNotIn(password, kwargs["input"])
                        else:
                            cfg = json.loads(base64.b64decode(body["data"][".dockerconfigjson"]))
                            self.assertEqual(set(cfg), {"auths"})
                            self.assertEqual(set(cfg["auths"]), {"ghcr.io"})
                            entry = cfg["auths"]["ghcr.io"]
                            self.assertEqual(set(entry), {"auth"})
                            self.assertEqual(base64.b64decode(entry["auth"]).decode(), "test-user:" + token)
                        if outcome == "create-timeout": raise subprocess.TimeoutExpired(args, 60, output=token, stderr=verifier)
                        return _FakeProc(1 if outcome in ("create-denied", "race") else 0, token, verifier)
                    secrets = [password, password] if mod is ui else ["test-user", token]
                    with mock.patch.object(mod.sys, "argv", ["helper", "--context", "test"]), \
                         mock.patch.object(mod.sys, "stdin", _TtyStdin()), \
                         mock.patch.object(mod, "read_secret_noecho", side_effect=secrets), \
                         mock.patch.object(mod.subprocess, "run", side_effect=subprocess_run), \
                         contextlib.redirect_stderr(io.StringIO()) as err, \
                         contextlib.redirect_stdout(io.StringIO()) as out:
                        code = mod.main()
                    self.assertEqual(code, 0 if outcome == "success" else 3 if outcome == "exists" else 4)
                    self.assertEqual(len(calls), 1 if outcome in ("exists", "probe-denied", "probe-timeout", "missing") else 2)
                    output = out.getvalue() + err.getvalue()
                    for secret in (password, token, verifier): self.assertNotIn(secret, output)
                    if outcome == "create-timeout":
                        self.assertIn("UNKNOWN_OUTCOME", output)
                        self.assertNotIn("no write attempted", output)


if __name__ == "__main__":
    unittest.main()

