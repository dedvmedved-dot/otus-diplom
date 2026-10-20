#!/usr/bin/env python3
"""Owner-side provisioning helper for the private GHCR image pull credential.

Contract (P8C-R1 D2 + R2-01/R3-A): the Owner creates/provides a read-only
packages token in their own secure interface. This helper reads the registry
username and token without echo, builds an auth-only `.dockerconfigjson` in
memory, and creates ONLY the Secret `portal/portal-registry-pull` (type
kubernetes.io/dockerconfigjson) via an atomic `kubectl create`.

Fail-closed: no-echo input is enforced directly via termios (no getpass
fallback-to-echo path); any non-zero `get` result stops BEFORE any write; the
only write verb is `create`. A timeout AFTER create submission is reported as
UNKNOWN_OUTCOME (never "no write attempted"). No apply/patch/replace, no fake
"password" field, no argv/env/temp files/logs with the token. Owner runs it in a
secure, non-recorded session; not run by agent or CI.

Usage:
    python3 portal/tools/provision-registry-pull.py --context <explicit-approved-context>

Exit codes:
    0  success
    2  usage / non-TTY / no-echo impossible
    3  Secret already exists (STOP, no overwrite)
    4  cannot verify state OR create failed / unknown outcome (STOP, no overwrite)
"""
import argparse
import base64
import json
import subprocess
import sys

NAMESPACE = "portal"
SECRET_NAME = "portal-registry-pull"
REGISTRY = "ghcr.io"
KUBECTL_TIMEOUT = 60


class NoEchoError(RuntimeError):
    pass


def require_tty() -> None:
    if not sys.stdin.isatty():
        print("STOP: token input requires a TTY (no echo); refusing to run non-interactively.", file=sys.stderr)
        sys.exit(2)


def read_secret_noecho(prompt: str) -> str:
    """Read a secret with echo disabled via termios. Fails closed: if no-echo is
    impossible, raise NoEchoError — there is NO getpass-style fallback."""
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
                eof = True
                break
            if c in ("\x03", "\x04"):
                sys.stderr.write("\n")
                sys.stderr.flush()
                raise NoEchoError("input cancelled (control character)")
            if c in ("\n", "\r"):
                break
            chars.append(c)
        sys.stderr.write("\n")
        sys.stderr.flush()
        if eof:
            raise NoEchoError("input ended (EOF) before completion")
    except (OSError, ValueError) as e:
        raise NoEchoError("no-echo read failed") from e
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except (termios.error, OSError, ValueError):
            pass
    return "".join(chars)


def run_kubectl(args, input_text=None):
    """Run kubectl. Returns (proc, timed_out); proc is None on OSError/timeout."""
    try:
        return subprocess.run(
            args, input=input_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=KUBECTL_TIMEOUT,
        ), False
    except subprocess.TimeoutExpired:
        return None, True
    except OSError as e:
        print(f"error: kubectl failed ({type(e).__name__})", file=sys.stderr)
        return None, False


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision portal-registry-pull Secret (Owner-side only)")
    parser.add_argument("--context", required=True, help="explicit approved kubectl context")
    args = parser.parse_args()

    require_tty()

    try:
        username = read_secret_noecho(f"Registry username for {REGISTRY} (read-only credential, no echo): ")
        token = read_secret_noecho(f"Registry token for {REGISTRY} (no echo): ")
    except NoEchoError as e:
        print(f"STOP: {e}", file=sys.stderr)
        return 2
    if not username or not token:
        print("error: username and token must not be empty", file=sys.stderr)
        return 2

    # Auth-only dockerconfigjson: single auth field = base64(username:token).
    auth = base64.b64encode(f"{username}:{token}".encode("utf-8")).decode("ascii")
    del username, token

    dockerconfig = {"auths": {REGISTRY: {"auth": auth}}}
    body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": SECRET_NAME, "namespace": NAMESPACE},
        "type": "kubernetes.io/dockerconfigjson",
        "data": {".dockerconfigjson": base64.b64encode(json.dumps(dockerconfig).encode("utf-8")).decode("ascii")},
    }

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
        print(f"STOP: Secret {NAMESPACE}/{SECRET_NAME} already exists; no overwrite.", file=sys.stderr)
        return 3

    proc, timed_out = run_kubectl([
        "kubectl", "--context", args.context, "create", "-f", "-",
    ], input_text=json.dumps(body))
    if proc is None:
        if timed_out:
            print("STOP: create timed out — UNKNOWN_OUTCOME. Re-check Secret state (get) before any further action; do not overwrite.", file=sys.stderr)
            return 4
        return 4
    if proc.returncode != 0:
        print("STOP: create failed (Secret may already exist); no overwrite attempted.", file=sys.stderr)
        return 4

    print(f"OK: Secret {NAMESPACE}/{SECRET_NAME} provisioned.")
    print("Record name, type, access verification and expiry/rotation responsibility only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
