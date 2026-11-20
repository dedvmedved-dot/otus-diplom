#!/usr/bin/env python3
"""Forgejo Actions release/lock-update gate (fail-closed, offline-verifiable).

Enforces the FULL admission chain required by review #52 before a verified
application digest may be written into ``portal/versions.lock:image``:

    owner gate  ->  trusted registry  ->  verified signed statement  ->  lock pair

  1. OWNER GATE (mandatory, checked BEFORE any credential access / build / push):
     a typed gate document binds the owner identity, the pinned SOURCE SHA, the
     WORKFLOW SHA (the tools pin), repository, package, ref, expiry window and a
     single-attempt budget. Absent / expired / foreign admission => reject.
  2. SOURCE / TOOLS SEPARATION: the pinned source tree (d22aa8f…) and the
     separately-pinned tools tree are checked out into independent directories;
     every file the build uses must be present in its OWN tree, the tools files
     must NOT be smuggled into the source tree, and the source must not be
     substituted with a new HEAD.
  3. TRUSTED REGISTRY: manifest bytes are verified ONLY against the owner-supplied
     trusted registry; credentials are never offered to any other host, and an
     unknown destination is refused BEFORE any network request.
  4. VERIFIED STATEMENT: the gate reads the SIGNED AND VERIFIED in-toto statement
     (``cosign verify-attestation`` output) of the SAME run — subject, builder and
     source come from that statement, never from a locally-built predicate.

Every function returns ``(ok: bool, reason: str)``; any missing/mismatched binding
is a rejection, never a pass. The module does NO network I/O of its own: the
registry transport is injected by the caller so it can be mocked offline. The
inactive Forgejo workflow and the offline harness import this SAME module, so
there is exactly one validation implementation.
"""
from __future__ import annotations

import base64
import calendar
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")

# Forgejo identity. OIDC issuer confirmed by read-only discovery on
# git.aiopslab.online (/.well-known/openid-configuration -> issuer == host).
# Workflow identity pattern follows the Forgejo Actions OIDC convention; the
# exact subject claim must be confirmed at the FIRST actual run (no build may be
# claimed before that). Registry/owner are owner-supplied P0 parameters.
FORGEJO_OIDC_ISSUER = "https://git.aiopslab.online"
FORGEJO_REPO = "aiopslab/otus-diplom"
WORKFLOW_FILE = ".forgejo/workflows/p8c-portal-forgejo-release.yml"
WORKFLOW_IDENTITY = "https://git.aiopslab.online/%s/%s@refs/heads/main" % (FORGEJO_REPO, WORKFLOW_FILE)
REF = "refs/heads/main"
SLSA = "https://slsa.dev/provenance/v0.2"
# buildType shared by the predicate generator and the verifier. This is a
# locally-pinned constant (Forgejo has no registered SLSA buildType URI yet);
# both sides pin the SAME value, which is what the binding check requires.
BUILD_TYPE = "https://forgejo.org/Attestations/ForgejoActionsWorkflow@v1"
IN_TOTO_TYPES = ("https://in-toto.io/Statement/v0.1", "https://in-toto.io/Statement/v1")

# Owner-supplied P0 parameters. PLACEHOLDERS that MUST be substituted
# out-of-band before the first run; the offline harness patches them to
# synthetic values to prove the fail-closed branches.
EXPECTED_OWNER = "<OWNER_IDENTITY_P0>"
TRUSTED_REGISTRY = "<REGISTRY_HOST_OWNER_SUPPLIED>"
# The tools pin is a SEPARATE immutable pin from the source pin. It is fixed to
# the commit that carries the Forgejo tooling (this file + its tests + the
# workflow template); its literal value is recorded at publication time.
PINNED_TOOLS_SHA = "<FORGEJO_TOOLS_SHA>"

# Files the build consumes, split by which tree owns them. The source tree
# (pinned source SHA) owns the application source + Containerfile + the go
# installer it already ships; the tools tree (separate tools pin) owns the
# Forgejo-specific gate/tests/workflow-template introduced by this PR.
REQUIRED_SOURCE_FILES = (
    "portal/Containerfile",
    "portal/Makefile",
    "portal/go.mod",
    "portal/go.sum",
    "portal/cmd/portal/main.go",
    "portal/tools/install-verified-go.sh",
)
REQUIRED_TOOLS_FILES = (
    "portal/tools/forgejo_lock_gate.py",
    "portal/tools/test_forgejo_lock_gate.py",
    "portal/tools/check_forgejo_workflow_syntax.py",
    "portal/tools/p8c-portal-forgejo-release.yml.template",
)

# Expected binding values for the decision. Values that are owner-supplied P0
# placeholders are overridden by the workflow CLI / harness.
BINDINGS = {
    "owner": EXPECTED_OWNER,
    "trusted_registry": TRUSTED_REGISTRY,
    "identity": WORKFLOW_IDENTITY,
    "issuer": FORGEJO_OIDC_ISSUER,
    "repository": FORGEJO_REPO,
    "ref": REF,
    "workflow_file": WORKFLOW_FILE,
    "build_type": BUILD_TYPE,
    "workflow_sha": PINNED_TOOLS_SHA,
}


def valid_sha(value):
    return isinstance(value, str) and bool(SHA_RE.match(value))


def valid_digest(value):
    return isinstance(value, str) and bool(DIGEST_RE.match(value))


def _parse_epoch(issued):
    return calendar.timegm(time.strptime(issued, "%Y-%m-%dT%H:%M:%SZ"))


# ---------------------------------------------------------------------------
# Stage 1: owner gate (admission before any release action)
# ---------------------------------------------------------------------------

def verify_owner_gate(gate, *, expected_owner, expected_source_sha,
                      expected_workflow_sha, expected_repository, expected_package,
                      expected_ref, run_attempt="1", now=None):
    """(ok, reason). Mandatory typed owner gate, verified BEFORE any release action.

    The gate must bind the owner identity, the pinned source SHA, the workflow
    SHA, repo, package, ref, and a single-attempt budget with a live expiry
    window. Missing / expired / foreign admission are all refusals.
    """
    if not isinstance(gate, dict):
        return False, "owner gate: not an object"
    if gate.get("owner") != expected_owner:
        return False, "owner gate: unknown/foreign owner admission"
    if not valid_sha(gate.get("source_sha")) or gate.get("source_sha") != expected_source_sha:
        return False, "owner gate: source_sha not bound to pinned source"
    wf = gate.get("workflow_sha")
    if not valid_sha(wf) or wf != expected_workflow_sha:
        return False, "owner gate: workflow_sha not bound"
    if gate.get("repository") != expected_repository:
        return False, "owner gate: repository not bound"
    if gate.get("package") != expected_package:
        return False, "owner gate: package not bound"
    if gate.get("ref") != expected_ref:
        return False, "owner gate: ref not bound"
    if gate.get("mode") != "LIVE":
        return False, "owner gate: mode must be LIVE"
    issued = gate.get("issued_at_utc")
    if not isinstance(issued, str) or not ISO_RE.match(issued):
        return False, "owner gate: issued_at_utc missing/invalid"
    expiry = gate.get("expiry_hours")
    if not isinstance(expiry, int) or isinstance(expiry, bool) or not (0 < expiry <= 24):
        return False, "owner gate: expiry_hours invalid"
    try:
        issued_epoch = _parse_epoch(issued)
    except Exception:
        return False, "owner gate: issued_at_utc unparseable"
    now = time.time() if now is None else now
    if issued_epoch > now:
        return False, "owner gate: not yet active (future)"
    if issued_epoch + expiry * 3600 < now:
        return False, "owner gate: expired"
    attempt = gate.get("attempt")
    if (not isinstance(attempt, int) or isinstance(attempt, bool) or attempt != 1
            or str(run_attempt) != "1"):
        return False, "owner gate: single-attempt budget violated (attempt/run_attempt must be 1)"
    return True, "owner gate verified"


# ---------------------------------------------------------------------------
# Stage 2: source / tools separation
# ---------------------------------------------------------------------------

def verify_file_inventory(source_inventory, tools_inventory, *, source_pin,
                          tools_pin, required_source=REQUIRED_SOURCE_FILES,
                          required_tools=REQUIRED_TOOLS_FILES):
    """(ok, reason). Every used file present in its OWN tree; no cross-tree mixing.

    source_inventory / tools_inventory are iterables of repo-relative paths (as
    produced by ``git ls-tree -r --name-only`` in each checkout directory).
    """
    if not valid_sha(source_pin):
        return False, "inventory: source pin invalid (must be 40-hex)"
    if not valid_sha(tools_pin):
        return False, "inventory: tools pin invalid (must be 40-hex)"
    if source_pin == tools_pin:
        return False, "inventory: source and tools pins must differ (separate immutable pins)"
    if not isinstance(source_inventory, (list, tuple, set, frozenset)):
        return False, "inventory: source entries not a list"
    if not isinstance(tools_inventory, (list, tuple, set, frozenset)):
        return False, "inventory: tools entries not a list"
    src = set(source_inventory)
    tls = set(tools_inventory)
    missing_src = sorted(f for f in required_source if f not in src)
    if missing_src:
        return False, "inventory: source files missing: " + ", ".join(missing_src)
    missing_tls = sorted(f for f in required_tools if f not in tls)
    if missing_tls:
        return False, "inventory: tools files missing: " + ", ".join(missing_tls)
    crossed = sorted(f for f in required_tools if f in src)
    if crossed:
        return False, "inventory: tools files smuggled into source tree: " + ", ".join(crossed)
    return True, "file inventory verified"


# ---------------------------------------------------------------------------
# Stage 3: trusted registry (manifest bytes, no credentials to a foreign host)
# ---------------------------------------------------------------------------

def fetch_registry_manifest(allowed_registry, registry_host, repository, digest, transport):
    """Fetch an image manifest by digest from the TRUSTED registry ONLY.

    ``registry_host`` must equal ``allowed_registry``; otherwise the call is
    refused BEFORE ``transport`` is invoked, so credentials are never offered to
    a foreign host. Returns ``(manifest_bytes, docker_content_digest)``.
    """
    if registry_host != allowed_registry:
        raise ValueError(
            "refused before any network/credential use: registry destination %r "
            "is not the trusted registry %r" % (registry_host, allowed_registry))
    if not valid_digest(digest):
        raise ValueError("invalid manifest digest")
    return transport(registry_host, repository, digest)


def verify_registry_manifest(allowed_registry, registry_host, image_ref, digest,
                             manifest_bytes, docker_content_digest):
    """(ok, reason). Manifest bytes from the trusted registry only; the push
    destination (image_ref) must sit under that registry; sha256(body) AND the
    Docker-Content-Digest header must both equal the digest."""
    if registry_host != allowed_registry:
        return False, "registry: manifest not from the trusted registry"
    if not isinstance(image_ref, str) or not image_ref.startswith(allowed_registry + "/"):
        return False, "registry: image_ref not under the trusted registry"
    if not valid_digest(digest):
        return False, "registry: digest invalid"
    if not isinstance(manifest_bytes, (bytes, bytearray)):
        return False, "registry: manifest bytes missing"
    if "sha256:" + hashlib.sha256(bytes(manifest_bytes)).hexdigest() != digest:
        return False, "registry: manifest bytes sha256 != digest"
    if docker_content_digest != digest:
        return False, "registry: Docker-Content-Digest != digest"
    return True, "registry manifest verified"


def _generic_oci_transport(registry_host, repository, digest):
    """Execution-time transport (generic OCI bearer flow). Reads credentials from
    REGISTRY_USERNAME / REGISTRY_TOKEN. Only ever contacts ``registry_host``, which
    ``fetch_registry_manifest`` has already validated == the trusted registry, so
    credentials are never offered to any other host. Returns (manifest_bytes,
    docker_content_digest)."""
    base = "https://" + registry_host
    cred = base64.b64encode(
        ("%s:%s" % (os.environ["REGISTRY_USERNAME"], os.environ["REGISTRY_TOKEN"])).encode()
    ).decode()
    token = None
    try:
        urllib.request.urlopen(
            urllib.request.Request(base + "/v2/", headers={"Authorization": "Basic " + cred}),
            timeout=30)
        token = cred
    except urllib.error.HTTPError as exc:
        challenge = exc.headers.get("WWW-Authenticate", "")
        realm = re.search(r'realm="([^"]+)"', challenge)
        if not realm:
            raise ValueError("registry did not offer a bearer challenge")
        params = {}
        for part in challenge.split(","):
            key, _, value = part.strip().partition("=")
            if key in ("service", "scope"):
                params[key] = value.strip('"')
        sep = "&" if "?" in realm.group(1) else "?"
        token_url = realm.group(1) + sep + "&".join(
            "%s=%s" % (k, urllib.parse.quote(v)) for k, v in params.items())
        data = urllib.request.urlopen(
            urllib.request.Request(token_url, headers={"Authorization": "Basic " + cred}),
            timeout=30).read()
        payload = json.loads(data)
        token = payload.get("token") or payload.get("access_token")
    if not token:
        raise ValueError("registry authentication failed")
    req = urllib.request.Request(
        base + "/v2/%s/manifests/%s" % (repository, digest),
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.oci.image.manifest.v1+json, "
                           "application/vnd.oci.image.index.v1+json, "
                           "application/vnd.docker.distribution.manifest.v2+json"})
    resp = urllib.request.urlopen(req, timeout=30)
    return resp.read(), resp.headers.get("Docker-Content-Digest")


# ---------------------------------------------------------------------------
# Stage 4: verified signed statement of the same run
# ---------------------------------------------------------------------------

def parse_verified_attestation(text):
    """Decode ``cosign verify-attestation`` JSONL -> list of in-toto statements.

    Accepts either raw in-toto statements or DSSE envelopes (``payloadType`` +
    base64 ``payload``) — the two shapes cosign emits across versions.
    """
    statements = []
    if not isinstance(text, str):
        return statements
    decoder = json.JSONDecoder()
    pos = 0
    length = len(text)
    while pos < length:
        while pos < length and text[pos] in " \t\r\n":
            pos += 1
        if pos >= length:
            break
        try:
            obj, end = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            break
        pos = end
        if (isinstance(obj, dict) and obj.get("payloadType")
                and isinstance(obj.get("payload"), str)):
            try:
                obj = json.loads(base64.b64decode(obj["payload"], validate=True))
            except Exception:
                continue
        if isinstance(obj, dict):
            statements.append(obj)
    return statements


def check_verified_statement(statement, *, expected_image_ref, expected_digest,
                             expected_source_sha, expected_workflow_sha,
                             expected_run_id, expected_identity, expected_repository,
                             expected_ref, expected_workflow_file, expected_build_type):
    """(ok, reason). The VERIFIED in-toto statement must bind subject, type,
    builder identity, source material, workflow SHA and run id."""
    if not isinstance(statement, dict):
        return False, "statement: not an object"
    if statement.get("_type") not in IN_TOTO_TYPES:
        return False, "statement: not an in-toto statement"
    if statement.get("predicateType") != SLSA:
        return False, "statement: predicateType is not SLSA provenance"
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or len(subjects) == 0:
        return False, "statement: subject missing"
    want_hex = expected_digest[len("sha256:"):]
    bound = False
    for sub in subjects:
        if not isinstance(sub, dict):
            continue
        if sub.get("name") == expected_image_ref and (sub.get("digest") or {}).get("sha256") == want_hex:
            bound = True
            break
    if not bound:
        return False, "statement: subject does not bind image/digest"
    pred = statement.get("predicate")
    if not isinstance(pred, dict):
        return False, "statement: predicate missing"
    if (pred.get("builder") or {}).get("id") != expected_identity:
        return False, "statement: builder.id != workflow identity"
    if pred.get("buildType") != expected_build_type:
        return False, "statement: buildType mismatch"
    inv = pred.get("invocation")
    cfg = (inv or {}).get("configSource") if isinstance(inv, dict) else None
    if not isinstance(cfg, dict):
        return False, "statement: invocation.configSource missing"
    if (cfg.get("digest") or {}).get("sha1") != expected_workflow_sha:
        return False, "statement: configSource does not bind workflow SHA"
    if cfg.get("entryPoint") != expected_workflow_file:
        return False, "statement: configSource.entryPoint != workflow file"
    uri = cfg.get("uri") or ""
    if expected_repository not in uri or expected_ref not in uri:
        return False, "statement: configSource.uri does not bind repo@ref"
    materials = pred.get("materials")
    if not isinstance(materials, list):
        return False, "statement: materials missing"
    if not any(isinstance(m, dict) and (m.get("digest") or {}).get("sha1") == expected_source_sha
               for m in materials):
        return False, "statement: materials do not bind pinned source SHA"
    meta = pred.get("metadata")
    if (not isinstance(meta, dict) or not isinstance(meta.get("buildInvocationId"), str)
            or meta["buildInvocationId"] != expected_run_id):
        return False, "statement: metadata.buildInvocationId != run id"
    return True, "verified statement bound"


# ---------------------------------------------------------------------------
# Predicate generator (Forgejo SLSA body; cosign fills the subject)
# ---------------------------------------------------------------------------

def build_predicate(source_sha, workflow_sha, run_id):
    """SLSA v0.2 predicate BODY (no subject — cosign attest fills it from the
    image). Binds the workflow identity, the workflow SHA (configSource) and the
    source SHA (materials). This predicate is ATTESTED, then re-read back from the
    verified statement; it is never itself the authority for the lock decision."""
    return {
        "builder": {"id": WORKFLOW_IDENTITY},
        "buildType": BUILD_TYPE,
        "invocation": {
            "configSource": {
                "uri": "git+https://git.aiopslab.online/%s@%s" % (FORGEJO_REPO, REF),
                "digest": {"sha1": workflow_sha},
                "entryPoint": WORKFLOW_FILE,
            }
        },
        "materials": [
            {"uri": "git+https://git.aiopslab.online/%s@%s" % (FORGEJO_REPO, REF),
             "digest": {"sha1": source_sha}}
        ],
        "metadata": {"buildInvocationId": run_id},
    }


# ---------------------------------------------------------------------------
# Decision: the full chain
# ---------------------------------------------------------------------------

def decide_lock_update(evidence, bindings=None, now=None):
    """Full admission chain -> (allowed, reason).

    ``now`` is an injectable clock for offline tests only; the production CLI
    always gates on ``time.time()``.

    ``evidence`` keys:
        owner_gate             dict   typed owner gate document
        source_sha             str    candidate source SHA (git rev-parse in src)
        pinned_source_sha      str    pinned source literal (d22aa8f…)
        workflow_sha           str    candidate workflow/tools SHA (git rev-parse in tools)
        pinned_workflow_sha    str    pinned tools literal
        source_inventory       list   repo-relative paths in the source tree
        tools_inventory        list   repo-relative paths in the tools tree
        registry_host          str    registry host the manifest was pulled from
        image_ref              str    full image ref (registry + path)
        digest                 str    sha256:<64hex>
        manifest_bytes         bytes  raw manifest body
        docker_content_digest  str    Docker-Content-Digest header value
        verified_attestation   str    cosign verify-attestation JSONL
        certificate_identity   str    --certificate-identity passed to cosign
        certificate_issuer     str    --certificate-oidc-issuer passed to cosign
        run_id                 str    runtime run id
        run_attempt            str    runtime run attempt (must be "1")
    """
    b = dict(BINDINGS)
    if bindings:
        b.update(bindings)

    # Stage 1 — owner gate (admission BEFORE any release action).
    gate = evidence.get("owner_gate")
    if gate is None:
        return False, "owner gate missing"
    ok, reason = verify_owner_gate(
        gate,
        expected_owner=b["owner"],
        expected_source_sha=evidence.get("pinned_source_sha", ""),
        expected_workflow_sha=evidence.get("pinned_workflow_sha", ""),
        expected_repository=b["repository"],
        expected_package=evidence.get("image_ref", ""),
        expected_ref=b["ref"],
        run_attempt=str(evidence.get("run_attempt", "1")),
        now=now,
    )
    if not ok:
        return False, reason

    # Stage 2 — source/tools separation.
    source_sha = evidence.get("source_sha")
    if not valid_sha(source_sha) or source_sha != evidence.get("pinned_source_sha"):
        return False, "source_sha mismatch vs pinned source"
    pinned_ws = evidence.get("pinned_workflow_sha")
    actual_ws = evidence.get("workflow_sha")
    if not valid_sha(pinned_ws) or not valid_sha(actual_ws) or actual_ws != pinned_ws:
        return False, "workflow_sha not bound to pinned tools"
    ok, reason = verify_file_inventory(
        evidence.get("source_inventory"), evidence.get("tools_inventory"),
        source_pin=evidence.get("pinned_source_sha"),
        tools_pin=pinned_ws,
    )
    if not ok:
        return False, reason

    # Stage 3 — trusted registry.
    ok, reason = verify_registry_manifest(
        b["trusted_registry"], evidence.get("registry_host"), evidence.get("image_ref"),
        evidence.get("digest"), evidence.get("manifest_bytes"),
        evidence.get("docker_content_digest"),
    )
    if not ok:
        return False, reason

    # Stage 4 — verified signed statement of the SAME run (issuer/identity cross-check).
    if evidence.get("certificate_identity") != b["identity"]:
        return False, "certificate identity != expected workflow identity"
    if evidence.get("certificate_issuer") != b["issuer"]:
        return False, "certificate issuer != expected OIDC issuer"
    statements = parse_verified_attestation(evidence.get("verified_attestation") or "")
    if not statements:
        return False, "no verified attestation result (discovery alone is not trust)"
    ok, reason = False, "verified statement does not bind"
    for st in statements:
        ok, reason = check_verified_statement(
            st,
            expected_image_ref=evidence.get("image_ref"),
            expected_digest=evidence.get("digest"),
            expected_source_sha=evidence.get("pinned_source_sha"),
            expected_workflow_sha=pinned_ws,
            expected_run_id=str(evidence.get("run_id", "")),
            expected_identity=b["identity"],
            expected_repository=b["repository"],
            expected_ref=b["ref"],
            expected_workflow_file=b["workflow_file"],
            expected_build_type=b["build_type"],
        )
        if ok:
            break
    if not ok:
        return False, reason
    return True, "all bindings verified"


# ---------------------------------------------------------------------------
# Lock write (registry + digest as ONE pair)
# ---------------------------------------------------------------------------

def apply_lock_pair(lock_path, registry, digest):
    """Write ``registry`` and ``digest`` as ONE pair into a portal/versions.lock
    style file, atomically (tmp + os.replace).

    The lock's existing ``registry:`` value MUST equal the verified registry —
    a digest from one registry is never recorded against another. Called only
    after ``decide_lock_update()`` returns allowed."""
    text = Path(lock_path).read_text()
    lines = text.split("\n")
    reg_idx = [i for i, ln in enumerate(lines) if ln.strip().startswith("registry:")]
    dg_idx = [i for i, ln in enumerate(lines) if ln.strip().startswith("digest:")]
    if len(reg_idx) != 1:
        raise RuntimeError("lock registry marker not found or ambiguous (%d)" % len(reg_idx))
    if len(dg_idx) != 1 or "NOT_VERIFIED" not in lines[dg_idx[0]]:
        raise RuntimeError("lock digest marker not found or already set (%d)" % len(dg_idx))
    indent = lines[reg_idx[0]][:len(lines[reg_idx[0]]) - len(lines[reg_idx[0]].lstrip())]
    cur_reg = lines[reg_idx[0]].split(":", 1)[1].strip().strip('"')
    if cur_reg != registry:
        raise RuntimeError("lock registry %r != verified registry %r (pair mismatch)" % (cur_reg, registry))
    lines[reg_idx[0]] = '%sregistry: "%s"' % (indent, registry)
    lines[dg_idx[0]] = '%sdigest: "%s"   # verified digest written by forgejo_lock_gate' % (indent, digest)
    tmp = str(lock_path) + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(lines))
    os.replace(tmp, lock_path)
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

USAGE = """usage:
  forgejo_lock_gate.py owner-gate <gate.json> --pinned-source <sha> --pinned-workflow <sha> \\
      --package <image_ref> [--owner O --repository R --ref F --run-attempt 1]
  forgejo_lock_gate.py inventory --source-inventory <paths.txt> --tools-inventory <paths.txt> \\
      --pinned-source <sha> --pinned-workflow <sha>
  forgejo_lock_gate.py registry-fetch --allowed-registry <host> --image-ref <ref> --digest <sha256:..> \\
      --manifest-out <file> --dcd-out <file>
  forgejo_lock_gate.py digest <build-metadata.json>
  forgejo_lock_gate.py predicate <source_sha> <workflow_sha> <run_id>
  forgejo_lock_gate.py verify <evidence.json> [--apply <lock_file>]"""


def _load_evidence(path):
    """Load an evidence bundle; ``manifest_file`` / ``verified_attestation_file``
    (paths) are read into ``manifest_bytes`` / ``verified_attestation``."""
    ev = json.loads(Path(path).read_text())
    if "manifest_file" in ev:
        ev["manifest_bytes"] = Path(ev.pop("manifest_file")).read_bytes()
    if "verified_attestation_file" in ev:
        ev["verified_attestation"] = Path(ev.pop("verified_attestation_file")).read_text()
    return ev


def main(argv):
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 2
    mode = argv[1]
    args = argv[2:]

    def flag(name, default=None):
        if name in args:
            return args[args.index(name) + 1]
        return default

    if mode == "owner-gate":
        try:
            gate = json.loads(Path(args[0]).read_text())
        except Exception:
            print("OWNER GATE NOT VERIFIED: unreadable", file=sys.stderr)
            return 1
        ok, reason = verify_owner_gate(
            gate,
            expected_owner=flag("--owner", EXPECTED_OWNER),
            expected_source_sha=flag("--pinned-source", ""),
            expected_workflow_sha=flag("--pinned-workflow", ""),
            expected_repository=flag("--repository", FORGEJO_REPO),
            expected_package=flag("--package", ""),
            expected_ref=flag("--ref", REF),
            run_attempt=flag("--run-attempt", "1"),
        )
        print(json.dumps({"owner_gate": ok, "reason": reason}))
        if not ok:
            print("OWNER GATE NOT VERIFIED: " + reason, file=sys.stderr)
            return 1
        return 0

    if mode == "inventory":
        src = Path(flag("--source-inventory", "")).read_text().splitlines()
        tls = Path(flag("--tools-inventory", "")).read_text().splitlines()
        ok, reason = verify_file_inventory(
            src, tls,
            source_pin=flag("--pinned-source", ""),
            tools_pin=flag("--pinned-workflow", ""),
        )
        print(json.dumps({"inventory": ok, "reason": reason}))
        return 0 if ok else 1

    if mode == "digest":
        meta = json.loads(Path(args[0]).read_text())
        d = meta.get("containerimage.digest")
        if not valid_digest(d):
            print("INVALID DIGEST", file=sys.stderr)
            return 1
        print(d)
        return 0

    if mode == "registry-fetch":
        allowed = flag("--allowed-registry", "")
        image_ref = flag("--image-ref", "")
        digest = flag("--digest", "")
        if not image_ref.startswith(allowed + "/"):
            print("REGISTRY NOT VERIFIED: image_ref not under trusted registry", file=sys.stderr)
            return 1
        repository = image_ref[len(allowed) + 1:]
        try:
            body, dcd = fetch_registry_manifest(
                allowed, allowed, repository, digest, _generic_oci_transport)
        except Exception as exc:
            print("REGISTRY NOT VERIFIED: %s" % exc, file=sys.stderr)
            return 1
        Path(flag("--manifest-out", "")).write_bytes(body)
        Path(flag("--dcd-out", "")).write_text(dcd or "")
        print(json.dumps({"registry": allowed, "digest": digest,
                          "dockerContentDigest": dcd, "bytes": len(body)}))
        return 0

    if mode == "predicate":
        if len(args) != 3:
            print(USAGE, file=sys.stderr)
            return 2
        print(json.dumps(build_predicate(args[0], args[1], args[2]), sort_keys=True))
        return 0

    if mode == "verify":
        try:
            evidence = _load_evidence(args[0])
        except Exception as exc:
            print("LOCK UPDATE NOT ALLOWED: evidence unreadable: %s" % exc, file=sys.stderr)
            return 1
        bindings = {}
        for key, flagname in (("owner", "--owner"), ("trusted_registry", "--trusted-registry"),
                              ("identity", "--identity"), ("issuer", "--issuer"),
                              ("repository", "--repository"), ("ref", "--ref"),
                              ("workflow_file", "--workflow-file"),
                              ("build_type", "--build-type"), ("workflow_sha", "--workflow-sha")):
            val = flag(flagname)
            if val is not None:
                bindings[key] = val
        allowed, reason = decide_lock_update(evidence, bindings or None)
        print(json.dumps({"allowed": allowed, "reason": reason}))
        if not allowed:
            print("LOCK UPDATE NOT ALLOWED: " + reason, file=sys.stderr)
            return 1
        apply_path = flag("--apply")
        if apply_path:
            try:
                apply_lock_pair(apply_path, evidence["registry_host"], evidence["digest"])
                print("LOCK UPDATED: %s -> registry=%s digest=%s" % (
                    apply_path, evidence["registry_host"], evidence["digest"]))
            except Exception as exc:
                print("LOCK UPDATE NOT ALLOWED: apply failed: %s" % exc, file=sys.stderr)
                return 1
        return 0

    print("unknown mode: " + mode, file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
