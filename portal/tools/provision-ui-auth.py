#!/usr/bin/env python3
"""Owner-side provisioning helper for the Portal operator UI password.

Contract (P8C-R1 D3 + R2-01/R3-A): the Owner stores the base64url encoding of
32 random bytes (43 ASCII chars, no padding) in their password manager. This is
the LOGIN password. This helper computes SHA-256 of those exact 43 ASCII chars
in memory and creates ONLY the Secret `portal/portal-ui-auth` key
`password-sha256` via an atomic `kubectl create` (JSON stdin).

Fail-closed: no-echo input is enforced directly via termios (no getpass
fallback-to-echo path); any non-zero `get` result (Forbidden/network/other)
stops BEFORE any write; the only write verb is `create`, which cannot overwrite
on a race. A timeout AFTER create submission is reported as UNKNOWN_OUTCOME
(never "no write attempted"); the Owner must metadata-recheck without overwrite.
No apply/patch/replace/force, no last-applied annotation, no argv/env/temp
files/logs with the password or verifier. Owner runs it in a secure,
non-recorded session; not run by the agent or CI.

Usage:
    python3 portal/tools/provision-ui-auth.py --context <explicit-approved-context>

Exit codes:
    0  success (Secret created)
    2  usage / validation / no-echo impossible
    3  Secret already exists OR cannot verify state (STOP, no write)
    4  create failed / unknown outcome (STOP, no overwrite)
"""
import argparse
import base64
import hashlib
import json
import subprocess
import sys

NAMESPACE = "portal"
SECRET_NAME = "portal-ui-auth"
SECRET_KEY = "password-sha256"
EXPECTED_LEN = 43
B64URL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
KUBECTL_TIMEOUT = 60


class NoEchoError(RuntimeError):
    pass


def require_tty() -> None:
    if not sys.stdin.isatty():
        print("STOP: password input requires a TTY (no echo); refusing to run non-interactively.", file=sys.stderr)
        sys.exit(2)


def read_secret_noecho(prompt: str) -> str:
    """Read a secret with echo disabled via termios. Fails closed: if no-echo is
    impossible (non-TTY, termios unavailable, read error), raise NoEchoError —
    there is NO getpass-style fallback that echoes input."""
    import termios
    import tty
    fd = sys.stdin.fileno()
    if not sys.stdin.isatty():
        raise NoEchoError("stdin is not a TTY; no-echo input impossible")
    try:
        old = termios.tcgetattr(fd)
    except (termios.error, OSError, ValueError) as e:
        raise NoEchoError("cannot read terminal attributes; no-echo input impossible") from e
    try:
        tty.setraw(fd)
        sys.stderr.write(prompt)
        sys.stderr.flush()
        chars = []
        eof = False
        while True:
            c = sys.stdin.read(1)
            if c == "":
                # EOF without a terminating newline -> fail closed, no write.
                eof = True
                break
            if c in ("\x03", "\x04"):
                # Ctrl-C / Ctrl-D -> cancel -> fail closed.
                sys.stderr.write("\n")
                sys.stderr.flush()
                raise NoEchoError("input cancelled (control character)")
            if c in ("\n", "\r"):
                break
            chars.append(c)
            if len(chars) > 4096:
                raise NoEchoError("input exceeds allowed length")
        sys.stderr.write("\n")
        sys.stderr.flush()
        if eof:
            raise NoEchoError("input ended (EOF) before completion")
    except (termios.error, OSError, ValueError, UnicodeError) as e:
        raise NoEchoError("no-echo read failed") from e
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except (termios.error, OSError, ValueError) as e:
            raise NoEchoError("terminal restore failed; stop before provisioning") from e
    return "".join(chars)


def validate_password(pwd: str) -> str:
    if len(pwd) != EXPECTED_LEN:
        return f"password must be exactly {EXPECTED_LEN} characters (got {len(pwd)})"
    if any(c not in B64URL_ALPHABET for c in pwd):
        return "password must be base64url alphabet (A-Za-z0-9-_) without padding"
    return ""


def run_kubectl(args, input_text=None):
    """Run kubectl. Returns (proc, timed_out); proc is None on OSError/timeout.
    timed_out distinguishes timeout-before-outcome from a known failure."""
    try:
        return subprocess.run(
            args, input=input_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=KUBECTL_TIMEOUT,
        ), False
    except subprocess.TimeoutExpired:
        return None, True
    except OSError as e:
        # Bounded message only; no captured stderr/body/credentials.
        print(f"error: kubectl failed ({type(e).__name__})", file=sys.stderr)
        return None, False


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision portal-ui-auth Secret (Owner-side only)")
    parser.add_argument("--context", required=True, help="explicit approved kubectl context")
    args = parser.parse_args()

    require_tty()

    try:
        pwd1 = read_secret_noecho("Enter operator password (43-char base64url, no echo): ")
        pwd2 = read_secret_noecho("Confirm operator password: ")
    except NoEchoError as e:
        print(f"STOP: {e}", file=sys.stderr)
        return 2
    if pwd1 != pwd2:
        print("error: passwords do not match", file=sys.stderr)
        return 2
    err = validate_password(pwd1)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    verifier = hashlib.sha256(pwd1.encode("ascii")).hexdigest()
    del pwd1, pwd2

    body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": SECRET_NAME, "namespace": NAMESPACE},
        "type": "Opaque",
        "data": {SECRET_KEY: base64.b64encode(verifier.encode("ascii")).decode("ascii")},
    }

    # Existence check: distinguish absent vs any other failure. Non-zero here
    # (Forbidden/network/...) must STOP without a write.
    probe, _ = run_kubectl([
        "kubectl", "--context", args.context, "-n", NAMESPACE, "get", "secret",
        SECRET_NAME, "--ignore-not-found", "-o", "name",
    ])
    if probe is None:
        return 4
    if probe.returncode != 0:
        print("STOP: cannot verify Secret state (Forbidden/network/other); no write attempted.", file=sys.stderr)
        return 4
    if probe.stdout.strip():
        print(f"STOP: Secret {NAMESPACE}/{SECRET_NAME} already exists; no implicit rotation.", file=sys.stderr)
        return 3

    # Atomic create (no-overwrite on race; no last-applied annotation).
    proc, timed_out = run_kubectl([
        "kubectl", "--context", args.context, "create", "-f", "-",
    ], input_text=json.dumps(body))
    if proc is None:
        if timed_out:
            # create may or may not have landed: UNKNOWN_OUTCOME, never "no write".
            print("STOP: create timed out — UNKNOWN_OUTCOME. Re-check Secret state (get) before any further action; do not overwrite.", file=sys.stderr)
            return 4
        return 4
    if proc.returncode != 0:
        # AlreadyExists/409 is a race -> STOP, never overwrite.
        print("STOP: create failed (Secret may already exist); no overwrite attempted.", file=sys.stderr)
        return 4

    print(f"OK: Secret {NAMESPACE}/{SECRET_NAME} key {SECRET_KEY} provisioned.")
    print("Verifier value is NOT printed. Owner retains the password in their password manager.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

