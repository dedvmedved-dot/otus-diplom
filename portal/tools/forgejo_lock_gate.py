#!/usr/bin/env python3
"""Forgejo Actions lock-update gate (fail-closed).

Decides whether the verified application digest may be written into
images.lock / portal/versions.lock. The digest must be obtained from the
registry (immutable manifest digest, Docker-Content-Digest), NEVER substituted
by a mutable tag and NEVER invented; it must bind to the pinned source SHA and
to the SLSA provenance of the exact trusted run. Until an actual build produces
these values, the lock stays NOT_VERIFIED.

This module is the SINGLE validation implementation shared by the (inactive)
Forgejo workflow and its negative test harness. The workflow's final
``update-lock`` step calls this same code; the negative harness imports it.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")

# Forgejo identity. OIDC issuer confirmed by read-only discovery on
# git.aiopslab.online (/.well-known/openid-configuration -> issuer == host).
# Workflow identity pattern follows the Forgejo Actions OIDC convention; the
# exact subject claim must be confirmed at the FIRST actual run (no build may
# be claimed before that). Registry/image_ref are owner-supplied P0 parameters.
FORGEJO_OIDC_ISSUER = "https://git.aiopslab.online"
FORGEJO_REPO = "aiopslab/otus-diplom"
WORKFLOW_FILE = ".forgejo/workflows/p8c-portal-forgejo-release.yml"
WORKFLOW_IDENTITY = "https://git.aiopslab.online/%s/%s@refs/heads/main" % (FORGEJO_REPO, WORKFLOW_FILE)
SLSA = "https://slsa.dev/provenance/v0.2"


def valid_sha(value):
    return isinstance(value, str) and bool(SHA_RE.match(value))


def valid_digest(value):
    return isinstance(value, str) and bool(DIGEST_RE.match(value))


def check_provenance(prov, expected_digest, source_sha, image_ref):
    """SLSA provenance must bind builder identity, source sha1 and subject digest.

    Returns (ok: bool, reason: str). Fail-closed: any missing/mismatched field
    is a rejection, never a pass.
    """
    if not isinstance(prov, dict):
        return False, "provenance not an object"
    builder = prov.get("builder")
    if not isinstance(builder, dict) or builder.get("id") != WORKFLOW_IDENTITY:
        return False, "provenance builder.id does not match Forgejo workflow identity"
    invocation = prov.get("invocation")
    config_source = (invocation or {}).get("configSource") if isinstance(invocation, dict) else None
    if not isinstance(config_source, dict):
        return False, "provenance invocation.configSource missing"
    if (config_source.get("digest") or {}).get("sha1") != source_sha:
        return False, "provenance does not bind pinned source SHA"
    subjects = prov.get("subject")
    if not isinstance(subjects, list) or len(subjects) == 0:
        return False, "provenance subject missing"
    want = expected_digest[len("sha256:"):]
    for sub in subjects:
        if not isinstance(sub, dict):
            continue
        if sub.get("name") == image_ref and (sub.get("digest") or {}).get("sha256") == want:
            return True, "ok"
    return False, "provenance subject does not bind image digest"


def decide_lock_update(source_sha, digest, provenance, image_ref, pinned_source_sha):
    """Return (allowed: bool, reason: str) for a lock update.

    The chain enforced, in order:
      1. pinned source SHA is a valid 40-hex literal (the accepted source);
      2. candidate source SHA is 40-hex AND equals the pinned literal;
      3. digest is sha256:<64hex> (a tag, a seed, or any non-digest string is
         rejected — digests are never substituted by tags);
      4. SLSA provenance binds the Forgejo workflow identity, the pinned source
         SHA and the subject digest.
    Any failure => allowed=False (lock update NOT permitted).
    """
    if not valid_sha(pinned_source_sha):
        return False, "pinned_source_sha invalid (must be 40-hex)"
    if not valid_sha(source_sha):
        return False, "source_sha invalid (must be 40-hex)"
    if source_sha != pinned_source_sha:
        return False, "source_sha mismatch vs pinned source"
    if not valid_digest(digest):
        return False, "digest invalid (must be sha256:<64hex>; tags are not accepted)"
    ok, reason = check_provenance(provenance, digest, source_sha, image_ref)
    if not ok:
        return False, reason
    return True, "all bindings verified"


def apply_digest_to_lock(lock_path, new_digest):
    """Replace the application image `digest:` value in a portal/versions.lock-style
    file with new_digest, atomically. Only called AFTER decide_lock_update()==True.
    Returns the number of replaced occurrences; raises if the marker is ambiguous.
    """
    text = Path(lock_path).read_text()
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith("  digest:") and "NOT_VERIFIED" in ln]
    if len(hits) != 1:
        raise RuntimeError("lock digest marker not found or ambiguous (%d hits)" % len(hits))
    i = hits[0]
    lines[i] = '  digest: "%s"   # verified digest written by forgejo_lock_gate (G2)' % new_digest
    tmp = str(lock_path) + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(lines))
    os.replace(tmp, lock_path)
    return 1


def main(argv):
    if len(argv) < 7:
        print("usage: forgejo_lock_gate.py <pinned_sha> <source_sha> <digest> <image_ref> "
              "<provenance.json> [--apply <lock_file>]", file=sys.stderr)
        return 2
    pinned, source, digest, image_ref, prov_path = argv[1], argv[2], argv[3], argv[4], argv[5]
    try:
        prov = json.loads(Path(prov_path).read_text())
    except Exception:
        print("LOCK UPDATE NOT ALLOWED: provenance unreadable", file=sys.stderr)
        return 1
    allowed, reason = decide_lock_update(source_sha=source, digest=digest,
                                         provenance=prov, image_ref=image_ref,
                                         pinned_source_sha=pinned)
    print(json.dumps({"allowed": allowed, "reason": reason,
                      "source_sha": source, "digest": digest, "image_ref": image_ref}))
    if not allowed:
        print("LOCK UPDATE NOT ALLOWED: " + reason, file=sys.stderr)
        return 1
    if len(argv) >= 8 and argv[6] == "--apply":
        try:
            apply_digest_to_lock(argv[7], digest)
            print("LOCK UPDATED: %s -> %s" % (argv[7], digest))
        except Exception as exc:  # noqa: BLE001
            print("LOCK UPDATE NOT ALLOWED: apply failed: %s" % exc, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
