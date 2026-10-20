#!/usr/bin/env python3
"""Owner-side provisioning helper for the private GHCR image pull credential.

Contract (P8C-R1 D2): the Owner creates/provides a read-only packages token in
their own secure interface. This helper reads that token without echo, builds
a `.dockerconfigjson` in memory, and creates ONLY the Secret
`portal/portal-registry-pull` (type kubernetes.io/dockerconfigjson) via
kubectl JSON stdin.

The token never touches argv, env, temporary files, logs or the chat. Owner
runs it in a secure, non-recorded session; not run by agent or CI.

Usage:
    python3 portal/tools/provision-registry-pull.py --context <explicit-approved-context>

Exit codes:
    0  success
    2  usage/validation error
    3  Secret already exists (STOP, no overwrite)
    4  kubectl / provisioning error
"""
import argparse
import base64
import json
import subprocess
import sys

NAMESPACE = "portal"
SECRET_NAME = "portal-registry-pull"
REGISTRY = "ghcr.io"
USERNAME = "dedvmedved-dot"


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision portal-registry-pull Secret (Owner-side only)")
    parser.add_argument("--context", required=True, help="explicit approved kubectl context")
    args = parser.parse_args()

    import getpass
    token = getpass.getpass(f"Enter read-only packages token for {REGISTRY} (no echo): ")
    if not token:
        print("error: empty token", file=sys.stderr)
        return 2

    auth = base64.b64encode(f"{USERNAME}:{token}".encode("ascii")).decode("ascii")
    del token

    dockerconfig = {
        "auths": {
            REGISTRY: {"username": USERNAME, "password": "REDACTED", "auth": auth}
        }
    }
    # Store the dockerconfigjson exactly as generated (password field removed
    # before any possible echo; only the `auth` field is authoritative).
    body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": SECRET_NAME, "namespace": NAMESPACE},
        "type": "kubernetes.io/dockerconfigjson",
        "data": {".dockerconfigjson": base64.b64encode(json.dumps(dockerconfig).encode("ascii")).decode("ascii")},
    }

    probe = subprocess.run(
        ["kubectl", "--context", args.context, "-n", NAMESPACE, "get", "secret", SECRET_NAME, "-o", "name"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if probe.returncode == 0:
        print(f"STOP: Secret {NAMESPACE}/{SECRET_NAME} already exists; no overwrite.", file=sys.stderr)
        return 3

    proc = subprocess.run(
        ["kubectl", "--context", args.context, "apply", "-f", "-"],
        input=json.dumps(body), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if proc.returncode != 0:
        print("error: kubectl apply failed (no body/credentials printed)", file=sys.stderr)
        return 4

    print(f"OK: Secret {NAMESPACE}/{SECRET_NAME} provisioned.")
    print("Record name, type, access verification and expiry/rotation responsibility only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
