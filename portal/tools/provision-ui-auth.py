#!/usr/bin/env python3
"""Owner-side provisioning helper for the Portal operator UI password.

Contract (P8C-R1 D3): the Owner stores the base64url encoding of 32 random
bytes (43 ASCII characters, no padding) in their own password manager. This
is the LOGIN password. This helper computes the SHA-256 of those exact 43
ASCII characters in memory and creates ONLY the Secret
`portal/portal-ui-auth` key `password-sha256` via kubectl JSON stdin.

The password and its verifier never touch argv, env, temporary files, logs or
the chat. The helper is intended to be run by the Owner in a secure,
non-recorded session; it is NOT run by the agent or CI.

Usage:
    python3 portal/tools/provision-ui-auth.py --context <explicit-approved-context>

Exit codes:
    0  success (Secret created)
    2  usage / validation error
    3  Secret already exists (STOP, no implicit rotation)
    4  kubectl / provisioning error
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


def validate_password(pwd: str) -> str:
    if len(pwd) != EXPECTED_LEN:
        return f"password must be exactly {EXPECTED_LEN} characters (got {len(pwd)})"
    if any(c not in B64URL_ALPHABET for c in pwd):
        return "password must be base64url alphabet (A-Za-z0-9-_) without padding"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision portal-ui-auth Secret (Owner-side only)")
    parser.add_argument("--context", required=True, help="explicit approved kubectl context")
    args = parser.parse_args()

    import getpass
    pwd1 = getpass.getpass("Enter operator password (43-char base64url, no echo): ")
    pwd2 = getpass.getpass("Confirm operator password: ")

    if pwd1 != pwd2:
        print("error: passwords do not match", file=sys.stderr)
        return 2

    err = validate_password(pwd1)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    # Compute SHA-256 of the exact ASCII string in memory.
    verifier = hashlib.sha256(pwd1.encode("ascii")).hexdigest()

    # Never log the password or verifier.
    del pwd1
    del pwd2

    # Build the Secret body in memory only (no temp files, no --from-literal).
    body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": SECRET_NAME, "namespace": NAMESPACE},
        "type": "Opaque",
        "data": {SECRET_KEY: base64.b64encode(verifier.encode("ascii")).decode("ascii")},
    }

    # Check for existing Secret (no implicit rotation).
    probe = subprocess.run(
        ["kubectl", "--context", args.context, "-n", NAMESPACE, "get", "secret", SECRET_NAME, "-o", "name"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if probe.returncode == 0:
        print(f"STOP: Secret {NAMESPACE}/{SECRET_NAME} already exists; no implicit rotation.", file=sys.stderr)
        return 3

    # Apply via JSON stdin (output captured; body not printed on error).
    proc = subprocess.run(
        ["kubectl", "--context", args.context, "apply", "-f", "-"],
        input=json.dumps(body), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if proc.returncode != 0:
        # Do NOT print stderr/stdout (may contain request body); print a bounded message.
        print("error: kubectl apply failed (no body/credentials printed)", file=sys.stderr)
        return 4

    print(f"OK: Secret {NAMESPACE}/{SECRET_NAME} key {SECRET_KEY} provisioned.")
    print("Verifier value is NOT printed. Owner retains the password in their password manager.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
