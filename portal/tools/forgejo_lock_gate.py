#!/usr/bin/env python3
"""Forgejo Actions release/lock-update gate (fail-closed, offline-verifiable).

Enforces the FULL admission chain required by review #52, tightened by review #55
and re-tightened by review #58 before a verified application digest may be
written into the Portal entry of ``images.lock``:

    owner gate  ->  trusted registry  ->  verified signed statement  ->  lock pair

  1. OWNER GATE (mandatory, checked BEFORE any credential access / build / push).
     A typed gate document binds the owner identity, the pinned SOURCE SHA, the
     pinned TOOLS SHA and the pinned WORKFLOW SHA (three separate immutable pins),
     repository, package, ref, a single-run binding (run_id + attempt) and a live
     expiry window. The gate's owner is CONFIRMED against the trusted runtime
     actor (github.actor) — never the self-asserted name alone — and the gate is
     bound to exactly one run, so re-dispatching the same gate within its expiry
     window is refused. review #58 items 1/4: repository, ref and workflow SHA are
     now TRIPLE-checked — the policy-ALLOWED value, the OBSERVED runtime context
     (github.repository / github.ref / GITHUB_WORKFLOW_SHA) and the owner document
     must all agree, and the workflow SHA is verified BEFORE any release rights.
  2. SOURCE / TOOLS / WORKFLOW SEPARATION: the pinned source tree (4c09d6b…), the
     separately-pinned tools tree and the pinned workflow definition are distinct
     immutable pins. Every file the build invokes must be present in its OWN tree,
     the tools files must NOT be smuggled into the source tree, and the source
     must not be substituted with a new HEAD. review #58 item 2: the source tree
     is additionally verified to be the COMPLETE pinned tree (full-tree sha256),
     so omissions/extra files outside the curated list — including inputs outside
     ``portal/`` — are caught.
  3. TRUSTED REGISTRY: manifest bytes are verified ONLY against the owner-supplied
     trusted registry. Every HTTP transition (the /v2/ ping, the bearer-token
     exchange AND the manifest fetch) is restricted to the SAME trusted HTTPS
     origin before any I/O; implicit redirects are refused; Basic credentials are
     never offered to a realm/token host that is not the trusted registry; and the
     manifest bytes + Docker-Content-Digest are verified at FETCH time (before any
     sign/attest), not deferred to just before the lock. review #58 item 3: Basic
     and issued-Bearer are SEPARATE schemes — the manifest fetch uses the Basic
     credential only when the registry accepted Basic directly, otherwise an
     ISSUED Bearer token, never the raw Basic credential mislabeled as Bearer.
  4. VERIFIED STATEMENT: the gate reads the SIGNED AND VERIFIED in-toto statement
     (``cosign verify-attestation`` output) of the SAME run — subject, builder,
     source material, tools material, workflow SHA and run id all come from that
     statement, never from a locally-built predicate. The pinned SHAs are taken
     from the INDEPENDENT policy bindings (module constants / CLI flags), never
     from the self-reported evidence bundle. review #61 item 1: the workflow SHA
     is a THIRD independent quantity — the policy pin is a SEPARATE protected
     out-of-band value (a repo secret supplied by the Owner), NOT the owner gate
     document's own ``workflow_sha``. The CLI REQUIRES ``--pinned-workflow`` (no
     document fallback) and the preflight triple-checks policy pin == owner
     document == observed runtime GITHUB_WORKFLOW_SHA before any release rights;
     an absent / mismatched pin stops the preflight fail-closed.

Every function returns ``(ok: bool, reason: str)``; any missing/mismatched binding
is a rejection, never a pass. The module does NO network I/O of its own: the
registry transport is injected by the caller so it can be mocked offline, and the
execution-time OCI transport's origin/redirect policy is covered by its own unit
tests. The inactive Forgejo workflow and the offline harness import this SAME
module, so there is exactly one validation implementation.
"""
from __future__ import annotations

import base64
import calendar
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
# SPDX document identity (review #103 item 2): the SPDX predicate must be a
# non-empty SPDX document of the expected shape — SPDX-2.x + SPDXRef-DOCUMENT.
SPDX_VERSION_RE = re.compile(r"SPDX-2\.[0-9]+\Z")

# Forgejo identity / OIDC. review #95 item 2 (B): the Actions OIDC issuer is
# confirmed by source — routers/api/actions/id_token.go + discovery
# /api/actions/.well-known/openid-configuration -> issuer is
# https://git.aiopslab.online/api/actions (NOT the bare AppURL).
FORGEJO_OIDC_ISSUER = "https://git.aiopslab.online/api/actions"
FORGEJO_REPO = "aiopslab/otus-diplom"
WORKFLOW_FILE = ".forgejo/workflows/p8c-portal-forgejo-release.yml"
# Owner decision (#162 comment 12512, 2026-11-28 13:14 UTC): the exact
# certificate identity (id-token `sub` / SAN) is CONFIRMED as the LITERAL
# repo:aiopslab/otus-diplom:ref:refs/heads/main (format
# repo:{repository}:ref:{ref}, NO event suffix, NO diagnostic sub). This is the
# exact --certificate-identity for cosign. It is pinned LITERALLY — matched by
# exact string equality, NO regex, NO diagnostic branch — and is never guessed.
# Keyless sign/verify/verify-attestation remains gated behind
# OIDC_TRUST_CONFIRMED (default False) until the PRIVATE Fulcio/Rekor/TUF trust
# roots are deployed (separate owner order); there is NO public-sigstore fallback.
WORKFLOW_IDENTITY = "repo:aiopslab/otus-diplom:ref:refs/heads/main"
# Owner decision (#162 comment 12512): the OIDC token audience for keyless
# signing is the LITERAL `sigstore` (cosign --oidc-client-id default; the
# private Fulcio's issuer allowlist requires audience=sigstore). Pinned
# literally; a token/certificate with any other audience is refused fail-closed.
OIDC_AUDIENCE = "sigstore"
REF = "refs/heads/main"
SLSA = "https://slsa.dev/provenance/v0.2"
# predicateType of the SPDX JSON attestation (cosign --type spdxjson) — the SBOM
# document describes the exact image it is attached to, so its source binding IS
# the signed subject (image@digest), asserted by check_verified_spdx_statement.
SPDX = "https://spdx.dev/Document"
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
# THREE separate immutable pins (review #55 item 4):
#  - PINNED_SOURCE_SHA   : the accepted source tree (accepted at 4c09d6b…).
#  - PINNED_TOOLS_SHA    : the commit that carries the Forgejo tooling (this file
#                          + its tests + the workflow template); fixed at
#                          publication time.
#  - PINNED_WORKFLOW_SHA : the commit/blob of the EXECUTED workflow definition
#                          (when published under .forgejo/workflows/). This is a
#                          DIFFERENT entity from the tools pin and is fixed at
#                          publication time, never derived from the tools checkout.
PINNED_SOURCE_SHA = "4c09d6b4a85e2d021516244988f48b92eade7acf"
PINNED_TOOLS_SHA = "<FORGEJO_TOOLS_SHA>"
PINNED_WORKFLOW_SHA = "<FORGEJO_WORKFLOW_SHA>"
# Full-tree completeness pin (review #58 item 2): sha256 over the SORTED
# (Unicode codepoint order — Python ``sorted()``, NOT locale ``sort``) list of
# `git ls-tree -r --name-only <PINNED_SOURCE_SHA>` output, newline-joined with a
# trailing newline. This is the COMPLETE input tree of the pinned source — any
# missing, extra or substituted file changes the hash, so a curated list can no
# longer hide an omission. Computed from 4c09d6b… (4574 files). Reproduce offline:
#   python3 -c "import hashlib,subprocess; t=subprocess.run(['git','ls-tree','-r','--name-only','4c09d6b4a85e2d021516244988f48b92eade7acf'],capture_output=True,text=True,check=True).stdout.splitlines(); print(hashlib.sha256(('\n'.join(sorted(t))+'\n').encode()).hexdigest())"
PINNED_SOURCE_TREE_SHA256 = "e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01"

# Files the build invokes, split by which tree owns them. The source tree
# (pinned source SHA) owns the application source + Containerfile + the go
# installer it already ships + the Python/JS test files the workflow actually
# invokes (review #55 item 2); the tools tree (separate tools pin) owns the
# Forgejo-specific gate/tests/workflow-template introduced by this PR.
REQUIRED_SOURCE_FILES = (
    # build entry points
    "portal/Containerfile",
    "portal/Makefile",
    "portal/go.mod",
    "portal/go.sum",
    "portal/cmd/portal/main.go",
    "portal/tools/install-verified-go.sh",
    # web assets embedded by the go build (portal/web/embed.go)
    "portal/web/embed.go",
    "portal/web/app.js",
    "portal/web/index.html",
    "portal/web/style.css",
    # workflow test step (python tests + their local imports)
    "portal/tools/test_helpers.py",
    "portal/tools/test_release.py",
    "portal/tools/release-check.py",
    "portal/tools/provision-ui-auth.py",
    "portal/tools/provision-registry-pull.py",
    # npm ci + JS fixture/smoke tests
    "portal/package.json",
    "portal/package-lock.json",
    "portal/web/renderer-smoke.test.mjs",
    "portal/web/fixture-smoke.test.mjs",
    # inputs OUTSIDE portal/ (review #58 item 2) — read by go tests at build time
    "docs/architecture/p8c/openapi.json",
    # go:embed'd + test-read inputs inside portal/ (review #58 item 2)
    "portal/migrations/migrations.go",
    "portal/migrations/0001_portal_observations.sql",
    "portal/manifests/networkpolicy.yaml",
    "portal/manifests/deployment.yaml",
    "portal/networkpolicy/testdata/accepted-policy-contract.json",
)
REQUIRED_TOOLS_FILES = (
    "portal/tools/forgejo_lock_gate.py",
    "portal/tools/test_forgejo_lock_gate.py",
    "portal/tools/test_forgejo_offline_integration.py",
    "portal/tools/test_owner_gate_barrier.py",
    "portal/tools/test_cosign_cli_flags.py",
    "portal/tools/check_forgejo_workflow_syntax.py",
    "portal/tools/p8c-portal-forgejo-release.yml.template",
    "portal/tools/cosign-slsa-policy.cue",
    "portal/tools/cosign-spdx-policy.cue",
)

# review #95 item 2 (B): keyless (OIDC) verification is BLOCKED by default. The
# owner must explicitly confirm the OIDC trust chain (CA trust to issuer +
# audience, the exact certificate SAN, binding to the approved workflow, and the
# agreed trust roots for sign/verify/verify-attestation) before the verified
# keyless statement may be accepted. The workflow CLI overrides this via
# --oidc-trust-confirmed only when inputs.oidc_trust_confirmed == true.
OIDC_TRUST_CONFIRMED = False

# Independent policy bindings. These are the ONLY authority for the pinned
# SHAs and identities: the evidence bundle is treated as untrusted self-report
# and is only ever COMPARED against these values (review #55 items 1 & 4).
# Values that are owner-supplied P0 placeholders are overridden by the workflow
# CLI / harness.
BINDINGS = {
    "owner": EXPECTED_OWNER,
    "trusted_registry": TRUSTED_REGISTRY,
    "identity": WORKFLOW_IDENTITY,
    "issuer": FORGEJO_OIDC_ISSUER,
    "audience": OIDC_AUDIENCE,
    "repository": FORGEJO_REPO,
    "ref": REF,
    "workflow_file": WORKFLOW_FILE,
    "build_type": BUILD_TYPE,
    "source_sha": PINNED_SOURCE_SHA,
    "tools_sha": PINNED_TOOLS_SHA,
    "workflow_sha": PINNED_WORKFLOW_SHA,
    "source_tree_sha256": PINNED_SOURCE_TREE_SHA256,
    "oidc_trust_confirmed": OIDC_TRUST_CONFIRMED,
}


def valid_sha(value):
    return isinstance(value, str) and bool(SHA_RE.match(value))


def valid_digest(value):
    return isinstance(value, str) and bool(DIGEST_RE.match(value))


def identity_is_confirmed(identity):
    """True only for the EXACT owner-confirmed certificate identity (literal SAN).

    Owner decision (#162 comment 12512): the certificate identity is pinned
    LITERALLY to repo:aiopslab/otus-diplom:ref:refs/heads/main (format
    repo:{repository}:ref:{ref}, no event suffix, no diagnostic sub). It is
    matched by EXACT string equality — no regex, no diagnostic branch — and any
    other (foreign) identity is rejected BEFORE any push/sign, even when
    oidc_trust_confirmed is true.
    """
    return isinstance(identity, str) and identity == WORKFLOW_IDENTITY


def _parse_epoch(issued):
    return calendar.timegm(time.strptime(issued, "%Y-%m-%dT%H:%M:%SZ"))


# ---------------------------------------------------------------------------
# Workflow-blob observation (review #95 item 1 / A1)
# ---------------------------------------------------------------------------

def observe_workflow_blob(workflow_dir, commit, workflow_file):
    """(blob_sha, reason) or (None, reason).

    Computes the git blob SHA of ``workflow_file`` at ``commit`` in the given
    ``workflow_dir`` checkout, and verifies the object is a **blob**. This is
    the OBSERVED executed-workflow identity required by review #95 item 1 (A1):
    the workflow file resolved at the fixed repo/path in the tree of the EXACT
    dispatch commit — NOT the non-existent GITHUB_WORKFLOW_SHA, NOT a mutable
    workflow_ref, NOT a value read back out of the gate secret itself.

    Absence of the path, a non-blob object, an invalid commit, or a failed
    lookup is a rejection BEFORE any side effect. Uses local ``git`` only (no
    network).
    """
    import subprocess
    if not valid_sha(commit):
        return None, "workflow blob: dispatch commit invalid (must be 40-hex)"
    if not isinstance(workflow_file, str) or not workflow_file:
        return None, "workflow blob: workflow path missing"
    try:
        resolved = subprocess.run(
            ["git", "-C", str(workflow_dir), "rev-parse", "--verify",
             commit + ":" + workflow_file],
            capture_output=True, text=True)
    except OSError as exc:
        return None, "workflow blob: git unavailable: %s" % exc
    if resolved.returncode != 0 or not resolved.stdout.strip():
        return None, "workflow blob: path absent at dispatch commit (%s)" % workflow_file
    blob = resolved.stdout.strip()
    if not valid_sha(blob):
        return None, "workflow blob: rev-parse did not yield a blob SHA (%r)" % blob
    try:
        typ = subprocess.run(
            ["git", "-C", str(workflow_dir), "cat-file", "-t", blob],
            capture_output=True, text=True)
    except OSError as exc:
        return None, "workflow blob: git unavailable: %s" % exc
    if typ.returncode != 0 or typ.stdout.strip() != "blob":
        return None, "workflow blob: object is not a blob (type=%r)" % typ.stdout.strip()
    return blob, "workflow blob observed"


# ---------------------------------------------------------------------------
# Exact tools-pin check (review #99 item 3)
# ---------------------------------------------------------------------------

# Every gate mode the workflow invokes. A stale tools pin (e.g. one predating
# the workflow-blob command) is a fail-closed REJECTION — the pinned tools
# checkout must actually implement what the workflow drives.
GATE_MODES = (
    "owner-gate",
    "inventory",
    "lock-image-check",
    "digest",
    "registry-fetch",
    "predicate",
    "workflow-blob",
    "verify",
)

# The CUE policies the workflow opens via `cosign verify-attestation --policy`
# (SLSA provenance + SPDX SBOM). review #103 item 3: the EXACT pinned tools
# checkout must also CARRY and LOAD both policies — the workflow opens them only
# after push/sign, so a tools pin whose gate implements every mode but is
# missing a policy would fail only at verify time. They are checked HERE (from
# the same checkout, before any external write).
REQUIRED_CUE_POLICIES = (
    "portal/tools/cosign-slsa-policy.cue",
    "portal/tools/cosign-spdx-policy.cue",
)

# review #106 item 3: presence + a bare ``predicateType:`` substring cannot tell
# the two policies apart — the review's control test placed an EXACT copy of the
# SLSA policy at the SPDX path and ``tools-pin-check`` still returned
# tools_pin=true. Each policy's ROLE must therefore be verified HERE, before any
# external write. We bind each policy to its pre-reviewed bytes: sha256 of the
# file must equal the reference recorded below (computed from the exact reviewed
# policy bytes — see the evidence result.md). A swapped pair, a corrupted file,
# or any un-reviewed edit changes the digest and is refused fail-closed. This is
# the "exact-bytes vs pre-verified reference" option the review lists: it is
# deterministic, needs no CUE engine in the gate, and runs offline in pure Python.
# A LEGITIMATE policy change (e.g. a re-pin of sourceSHA) must update these
# references as part of the same reviewed commit (§3 of the runbook).
CUE_POLICY_REFERENCE_SHA256 = {
    "portal/tools/cosign-slsa-policy.cue":
        "b5051d68d2e8bbaa423e87c3488cdc615d5587338665632e740ba5df06b6259e",
    "portal/tools/cosign-spdx-policy.cue":
        "59fcc14263abbee70717d510fd9a57112065bd1291d8e7834598068533cf4c30",
}


def verify_tools_pin(tools_dir, required_modes=GATE_MODES,
                     required_cue_policies=REQUIRED_CUE_POLICIES,
                     cue_policy_reference_sha256=CUE_POLICY_REFERENCE_SHA256):
    """(ok, reason). The pinned tools checkout must implement every gate mode the
    workflow invokes AND carry both CUE policies the workflow opens with
    ``cosign verify-attestation --policy``. Reads the gate SOURCE and the policy
    files from the ACTUAL tools checkout (never from the importing module), so a
    stale/mismatched PINNED_TOOLS_SHA is caught before any release action
    (review #99 item 3 + review #103 item 3). Each CUE policy is further bound to
    its pre-reviewed bytes via a reference SHA-256 so a swapped or corrupted
    policy is refused BEFORE the first external write (review #106 item 3)."""
    gate_path = Path(tools_dir) / "portal" / "tools" / "forgejo_lock_gate.py"
    if not gate_path.is_file():
        return False, "tools pin: forgejo_lock_gate.py missing at %s" % gate_path
    try:
        text = gate_path.read_text()
    except OSError as exc:
        return False, "tools pin: gate unreadable: %s" % exc
    missing = [m for m in required_modes if ('mode == "%s"' % m) not in text]
    if missing:
        return False, "tools pin: gate missing modes: %s" % ", ".join(missing)
    # review #103 item 3 + review #106 item 3: both CUE policies must be present
    # AND match their own role from the SAME checkout (the workflow opens them
    # only after push/sign, so a missing / swapped / corrupted policy would
    # otherwise surface too late). Each policy is checked (a) readable +
    # non-empty, and (b) byte-identical to its pre-reviewed reference — so the
    # SPDX path carrying an exact SLSA copy, or a truncated policy, is refused.
    for rel in required_cue_policies:
        policy_path = Path(tools_dir) / rel
        if not policy_path.is_file():
            return False, "tools pin: CUE policy missing at %s" % policy_path
        try:
            policy_bytes = policy_path.read_bytes()
        except OSError as exc:
            return False, "tools pin: CUE policy unreadable (%s): %s" % (rel, exc)
        if not policy_bytes.strip():
            return False, "tools pin: CUE policy empty: %s" % rel
        expected = cue_policy_reference_sha256.get(rel)
        if not isinstance(expected, str) or not expected:
            return False, "tools pin: no reference SHA-256 recorded for CUE policy: %s" % rel
        if hashlib.sha256(policy_bytes).hexdigest() != expected:
            return False, ("tools pin: CUE policy does not match its reviewed role "
                           "(swapped or corrupted): %s" % rel)
    return True, "tools pin implements all required gate modes and both CUE policies match their reviewed roles"


# ---------------------------------------------------------------------------
# Stage 1: owner gate (admission before any release action)
# ---------------------------------------------------------------------------

def verify_owner_gate(gate, *, expected_owner, expected_source_sha,
                      expected_tools_sha, expected_workflow_sha, expected_repository,
                      expected_package, expected_ref, actor=None, run_id=None,
                      run_attempt="1", observed_repository=None, observed_ref=None,
                      observed_workflow_sha=None, now=None):
    """(ok, reason). Mandatory typed owner gate, verified BEFORE any release action.

    The gate must bind the owner identity, the pinned source/tools/workflow SHAs,
    repo, package, ref, a single-run binding (run_id) and a single-attempt budget
    with a live expiry window. The owner is CONFIRMED against the trusted runtime
    ``actor`` (github.actor) — a self-asserted name in the document is not enough —
    and the gate is bound to exactly one run (``run_id``), so a re-dispatch of the
    same gate is refused. Missing / expired / foreign / replay admission are all
    refusals.

    review #58 item 1/4 + review #61 item 1: repository, ref and workflow SHA
    are now TRIPLE-checked — the policy-ALLOWED value (``expected_*``), the
    OBSERVED runtime context (``observed_*``) and the owner document must all
    agree. For the workflow SHA specifically the ``expected_workflow_sha`` is the
    INDEPENDENT protected out-of-band policy pin (never the document's own
    ``workflow_sha``), so the check is over THREE distinct quantities and a
    document+observed agreement that contradicts the policy pin is still refused.
    This closes the gap where the document was compared only to the runtime
    context but never to the policy-allowed repository/ref, and adds the
    workflow-SHA check that was previously absent before release rights were
    granted.
    """
    if not isinstance(gate, dict):
        return False, "owner gate: not an object"
    if gate.get("owner") != expected_owner:
        return False, "owner gate: unknown/foreign owner admission"
    if not isinstance(actor, str) or not actor:
        return False, "owner gate: trusted actor (github.actor) missing"
    if actor != expected_owner:
        return False, "owner gate: actor does not confirm the owner"
    if not valid_sha(gate.get("source_sha")) or gate.get("source_sha") != expected_source_sha:
        return False, "owner gate: source_sha not bound to pinned source"
    if not valid_sha(gate.get("tools_sha")) or gate.get("tools_sha") != expected_tools_sha:
        return False, "owner gate: tools_sha not bound to pinned tools"
    wf = gate.get("workflow_sha")
    if not valid_sha(wf) or wf != expected_workflow_sha:
        return False, "owner gate: workflow_sha not bound"
    # repository/ref/workflow SHA: TRIPLE check (policy allowed == owner document
    # == observed runtime context). The observed context is the trusted runtime
    # value (github.repository / github.ref / GITHUB_WORKFLOW_SHA); it must equal
    # BOTH the policy-allowed value and the owner-documented value. Absence of any
    # observed value is a REJECTION (fail-closed) — the runtime context must be
    # bound, never skipped (review #58 items 1 & 4).
    if gate.get("repository") != expected_repository:
        return False, "owner gate: repository not bound to policy"
    if not isinstance(observed_repository, str) or not observed_repository:
        return False, "owner gate: observed repository (runtime context) missing"
    if observed_repository != expected_repository:
        return False, "owner gate: observed repository != policy-allowed repository"
    if gate.get("repository") != observed_repository:
        return False, "owner gate: document repository != observed runtime context"
    if gate.get("package") != expected_package:
        return False, "owner gate: package not bound"
    if gate.get("ref") != expected_ref:
        return False, "owner gate: ref not bound to policy"
    if not isinstance(observed_ref, str) or not observed_ref:
        return False, "owner gate: observed ref (runtime context) missing"
    if observed_ref != expected_ref:
        return False, "owner gate: observed ref != policy-allowed ref"
    if gate.get("ref") != observed_ref:
        return False, "owner gate: document ref != observed runtime context"
    if not isinstance(observed_workflow_sha, str) or not observed_workflow_sha:
        return False, "owner gate: observed workflow SHA (runtime context) missing"
    if observed_workflow_sha != wf:
        return False, "owner gate: observed workflow SHA != owner-documented workflow SHA"
    if observed_workflow_sha != expected_workflow_sha:
        return False, "owner gate: observed workflow SHA != policy-pinned workflow SHA"
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
    if not isinstance(run_id, str) or not run_id:
        return False, "owner gate: run id missing (cannot bind to the run)"
    if gate.get("run_id") != run_id:
        return False, "owner gate: run_id not bound to this run (replay refused)"
    return True, "owner gate verified"


# ---------------------------------------------------------------------------
# Stage 2: source / tools separation
# ---------------------------------------------------------------------------

def verify_file_inventory(source_inventory, tools_inventory, *, source_pin,
                          tools_pin, required_source=REQUIRED_SOURCE_FILES,
                          required_tools=REQUIRED_TOOLS_FILES,
                          source_tree_sha256=None):
    """(ok, reason). Every used file present in its OWN tree; no cross-tree mixing.

    source_inventory / tools_inventory are iterables of repo-relative paths (as
    produced by ``git ls-tree -r --name-only`` in each checkout directory).

    review #58 item 2: when ``source_tree_sha256`` is given, the SOURCE tree is
    additionally verified to be the COMPLETE pinned tree — the sha256 of the
    sorted, newline-joined inventory must equal the pinned value, so any missing /
    extra / substituted file (including inputs outside ``portal/``) is caught, not
    just the curated ``required_source`` list.
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
    if source_tree_sha256 is not None:
        ok, reason = verify_source_tree_complete(source_inventory, source_tree_sha256)
        if not ok:
            return False, reason
    return True, "file inventory verified"


def verify_source_tree_complete(source_inventory, expected_tree_sha256):
    """(ok, reason). The source tree is the COMPLETE pinned tree (review #58 item 2).

    Hashes the SORTED, newline-joined inventory and compares it to the pinned
    full-tree sha256 (``PINNED_SOURCE_TREE_SHA256``). A curated list of "required"
    files only proves those paths exist; this proves the ENTIRE tree — including
    inputs outside ``portal/`` — is present and unmodified, and catches any
    omission, extra file or substitution.
    """
    if not isinstance(source_inventory, (list, tuple, set, frozenset)):
        return False, "inventory: source entries not a list"
    if not isinstance(expected_tree_sha256, str) or len(expected_tree_sha256) != 64:
        return False, "inventory: expected source-tree sha256 invalid"
    entries = sorted(str(p) for p in source_inventory)
    actual = hashlib.sha256(("\n".join(entries) + "\n").encode()).hexdigest()
    if actual != expected_tree_sha256:
        return False, "inventory: source tree is not the complete pinned tree (missing/extra/substituted files)"
    return True, "source tree completeness verified"


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


def _trusted_origin_ok(url, trusted_host):
    """True only for a same-host HTTPS origin (no implicit scheme/host change)."""
    parts = urllib.parse.urlsplit(url)
    return (parts.scheme == "https"
            and parts.hostname == trusted_host
            and parts.port in (None, 443))


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse EVERY implicit redirect: the gate only ever talks to the trusted
    registry origin, and any redirect is a potential credential-leak vector."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "redirect refused (trusted-origin-only transport)",
            headers, fp)


def _strict_urlopen(url, headers=None, timeout=30):
    """Open ``url`` with a redirect-refusing opener (trusted-origin only)."""
    opener = urllib.request.build_opener(_RefuseRedirect)
    return opener.open(
        urllib.request.Request(url, headers=headers if headers is not None else {}),
        timeout=timeout)


def _bearer_token_url(challenge, trusted_host):
    """Resolve the bearer-token URL from a WWW-Authenticate challenge, refusing
    (BEFORE any I/O / Basic-credential use) any realm that is not the trusted
    HTTPS origin."""
    realm = re.search(r'realm="([^"]+)"', challenge or "")
    if not realm:
        raise ValueError("registry did not offer a bearer challenge")
    realm_url = realm.group(1)
    if not _trusted_origin_ok(realm_url, trusted_host):
        raise ValueError(
            "registry bearer realm %r is not the trusted HTTPS origin %r" % (realm_url, trusted_host))
    params = {}
    for part in (challenge or "").split(","):
        key, _, value = part.strip().partition("=")
        if key in ("service", "scope"):
            params[key] = value.strip('"')
    sep = "&" if "?" in realm_url else "?"
    return realm_url + sep + "&".join(
        "%s=%s" % (k, urllib.parse.quote(v)) for k, v in params.items())


def _generic_oci_transport(registry_host, repository, digest, urlopen=None):
    """Execution-time transport (generic OCI bearer flow). Reads credentials from
    REGISTRY_USERNAME / REGISTRY_TOKEN. Only ever contacts ``registry_host``
    (already validated == the trusted registry by ``fetch_registry_manifest``),
    over HTTPS, with redirects refused and the bearer realm restricted to the
    SAME trusted origin — so Basic credentials are never offered to any other
    host and Bearer/Basic are never mixed across origins. Returns
    (manifest_bytes, docker_content_digest). ``urlopen`` is injectable for tests.

    review #58 item 3: Basic and issued-Bearer are now SEPARATE schemes. The Basic
    credential is used only for the /v2/ ping and the token exchange; the manifest
    fetch uses EITHER the Basic credential (only when the registry accepted Basic
    directly on /v2/) OR a Bearer token ISSUED by the token endpoint — never the
    raw Basic credential mislabeled as a Bearer token (the previous ``token = cred``
    on a 200 then ``Bearer <cred>`` bug).
    """
    urlopen = urlopen or _strict_urlopen
    base = "https://" + registry_host
    cred = base64.b64encode(
        ("%s:%s" % (os.environ["REGISTRY_USERNAME"], os.environ["REGISTRY_TOKEN"])).encode()
    ).decode()
    basic = "Basic " + cred
    # auth_header is decided by which scheme the registry actually granted:
    #   - Basic accepted directly on /v2/ (200)      -> continue with Basic
    #   - 401 + Bearer challenge -> exchange Basic for a Bearer token -> Bearer
    auth_header = basic
    try:
        urlopen(base + "/v2/", headers={"Authorization": basic})
        # 200: registry accepted Basic directly. Keep Basic for the manifest fetch
        # (do NOT reuse the Basic credential as a Bearer token).
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        token_url = _bearer_token_url(exc.headers.get("WWW-Authenticate", ""), registry_host)
        data = urlopen(token_url, headers={"Authorization": basic}).read()
        payload = json.loads(data)
        token = payload.get("token") or payload.get("access_token")
        if not token or not isinstance(token, str):
            raise ValueError("registry authentication failed (no bearer token issued)")
        auth_header = "Bearer " + token
    resp = urlopen(
        base + "/v2/%s/manifests/%s" % (repository, digest),
        headers={"Authorization": auth_header,
                 "Accept": "application/vnd.oci.image.manifest.v1+json, "
                           "application/vnd.oci.image.index.v1+json, "
                           "application/vnd.docker.distribution.manifest.v2+json"})
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
                             expected_source_sha, expected_tools_sha, expected_workflow_sha,
                             expected_run_id, expected_identity, expected_repository,
                             expected_ref, expected_workflow_file, expected_build_type):
    """(ok, reason). The VERIFIED in-toto statement must bind subject, type,
    builder identity, source material, tools material, workflow SHA and run id."""
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
    mat_sha1s = set()
    for m in materials:
        if isinstance(m, dict) and isinstance((m.get("digest") or {}).get("sha1"), str):
            mat_sha1s.add(m["digest"]["sha1"])
    if expected_source_sha not in mat_sha1s:
        return False, "statement: materials do not bind pinned source SHA"
    if expected_tools_sha not in mat_sha1s:
        return False, "statement: materials do not bind pinned tools SHA"
    meta = pred.get("metadata")
    if (not isinstance(meta, dict) or not isinstance(meta.get("buildInvocationId"), str)
            or meta["buildInvocationId"] != expected_run_id):
        return False, "statement: metadata.buildInvocationId != run id"
    return True, "verified statement bound"


def check_verified_spdx_statement(statement, *, expected_image_ref, expected_digest):
    """(ok, reason). The VERIFIED SPDX attestation must bind its subject to the
    image/digest AND carry a SIGNED NON-EMPTY SPDX document of the expected
    shape as its predicate.

    review #103 item 2: the SBOM→digest binding is the signed SUBJECT
    (image@digest) — the SPDX document describes that exact image — while the
    digest→source binding is the SEPARATE SLSA provenance (check_verified_statement
    binds the same digest to the pinned source SHA via its materials). The SPDX
    ``predicateType`` string alone proves NEITHER: this check therefore reads the
    predicate and requires an SPDX document of the expected shape (SPDX-2.x +
    SPDXRef-DOCUMENT, non-empty name/documentNamespace, non-empty packages), so
    a missing / empty / foreign document is rejected fail-closed."""
    if not isinstance(statement, dict):
        return False, "spdx statement: not an object"
    if statement.get("_type") not in IN_TOTO_TYPES:
        return False, "spdx statement: not an in-toto statement"
    if statement.get("predicateType") != SPDX:
        return False, "spdx statement: predicateType is not SPDX"
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or len(subjects) == 0:
        return False, "spdx statement: subject missing"
    want_hex = expected_digest[len("sha256:"):]
    bound = False
    for sub in subjects:
        if (isinstance(sub, dict) and sub.get("name") == expected_image_ref
                and (sub.get("digest") or {}).get("sha256") == want_hex):
            bound = True
            break
    if not bound:
        return False, "spdx statement: subject does not bind image/digest"
    # review #103 item 2: the predicate must be a NON-EMPTY SPDX document of the
    # expected shape — not merely present. The SPDX document identity + a
    # non-empty packages list are required; an absent / empty / foreign document
    # (wrong spdxVersion or SPDXID, empty packages) is rejected.
    predicate = statement.get("predicate")
    if not isinstance(predicate, dict) or not predicate:
        return False, "spdx statement: predicate (SPDX document) missing/empty"
    spdx_version = predicate.get("spdxVersion")
    if not isinstance(spdx_version, str) or not SPDX_VERSION_RE.match(spdx_version):
        return False, "spdx statement: predicate.spdxVersion not SPDX-2.x"
    if predicate.get("SPDXID") != "SPDXRef-DOCUMENT":
        return False, "spdx statement: predicate.SPDXID != SPDXRef-DOCUMENT"
    if not isinstance(predicate.get("name"), str) or not predicate["name"].strip():
        return False, "spdx statement: predicate.name missing/empty"
    if (not isinstance(predicate.get("documentNamespace"), str)
            or not predicate["documentNamespace"].strip()):
        return False, "spdx statement: predicate.documentNamespace missing/empty"
    packages = predicate.get("packages")
    if not isinstance(packages, list) or len(packages) == 0:
        return False, "spdx statement: predicate.packages missing/empty"
    return True, "spdx statement bound to image/digest (non-empty SPDX document)"


# ---------------------------------------------------------------------------
# Predicate generator (Forgejo SLSA body; cosign fills the subject)
# ---------------------------------------------------------------------------

def build_predicate(source_sha, workflow_sha, tools_sha, run_id):
    """SLSA v0.2 predicate BODY (no subject — cosign attest fills it from the
    image). Binds the workflow identity, the WORKFLOW SHA (configSource) and the
    SOURCE + TOOLS SHAs (materials) as three separate pins. This predicate is
    ATTESTED, then re-read back from the verified statement; it is never itself
    the authority for the lock decision."""
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
             "digest": {"sha1": source_sha}},
            {"uri": "git+https://git.aiopslab.online/%s@%s" % (FORGEJO_REPO, REF),
             "digest": {"sha1": tools_sha}},
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

    ``evidence`` keys (all untrusted self-reports, compared against the
    INDEPENDENT policy bindings):
        owner_gate             dict   typed owner gate document
        source_sha             str    candidate source SHA (git rev-parse in src)
        tools_sha              str    candidate tools SHA (git rev-parse in tools)
        workflow_sha           str    candidate workflow SHA (runtime context)
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
        actor                  str    github.actor (trusted runtime context)
        run_id                 str    runtime run id
        run_attempt            str    runtime run attempt (must be "1")
        observed_repository    str    github.repository (runtime, triple-checked vs policy+doc)
        observed_ref           str    github.ref (runtime, triple-checked vs policy+doc)
        observed_workflow_sha  str    GITHUB_WORKFLOW_SHA (runtime, triple-checked vs policy+doc)
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
        expected_source_sha=b["source_sha"],
        expected_tools_sha=b["tools_sha"],
        expected_workflow_sha=b["workflow_sha"],
        expected_repository=b["repository"],
        expected_package=evidence.get("image_ref", ""),
        expected_ref=b["ref"],
        actor=evidence.get("actor"),
        run_id=str(evidence.get("run_id", "")),
        run_attempt=str(evidence.get("run_attempt", "1")),
        observed_repository=evidence.get("observed_repository"),
        observed_ref=evidence.get("observed_ref"),
        observed_workflow_sha=evidence.get("observed_workflow_sha"),
        now=now,
    )
    if not ok:
        return False, reason

    # Stage 2 — source/tools/workflow separation, checked against the
    # INDEPENDENT policy pins (NOT the self-reported evidence).
    source_sha = evidence.get("source_sha")
    if not valid_sha(source_sha) or source_sha != b["source_sha"]:
        return False, "source_sha mismatch vs pinned source"
    tools_sha = evidence.get("tools_sha")
    if not valid_sha(tools_sha) or tools_sha != b["tools_sha"]:
        return False, "tools_sha not bound to pinned tools"
    workflow_sha = evidence.get("workflow_sha")
    if not valid_sha(workflow_sha) or workflow_sha != b["workflow_sha"]:
        return False, "workflow_sha not bound to pinned workflow"
    ok, reason = verify_file_inventory(
        evidence.get("source_inventory"), evidence.get("tools_inventory"),
        source_pin=b["source_sha"],
        tools_pin=b["tools_sha"],
        source_tree_sha256=b.get("source_tree_sha256"),
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

    # Stage 4 — verified signed statement of the SAME run (issuer/identity
    # cross-check). review #95 item 2 (B): the keyless (OIDC) statement is only
    # accepted when the owner has explicitly confirmed the OIDC trust chain
    # (CA trust to issuer+audience, exact SAN, workflow binding, trust roots for
    # sign/verify/verify-attestation). Without that confirmation the release is
    # refused fail-closed — a verified-looking statement whose trust chain is
    # unconfirmed is NOT trust.
    if not b.get("oidc_trust_confirmed"):
        return False, ("OIDC trust not confirmed (issuer/SAN/audience/trust roots) "
                       "— keyless verification BLOCKED")
    # Owner decision (#162 comment 12512): oidc_trust_confirmed=true with a
    # FOREIGN (non-literal) SAN must NOT be allowed to reach push/sign. The
    # identity is the LITERAL repo:aiopslab/otus-diplom:ref:refs/heads/main,
    # matched by EXACT equality (no regex, no diagnostic branch) — never guessed.
    if not identity_is_confirmed(b["identity"]):
        return False, "workflow identity not confirmed (not the literal SAN) — keyless release BLOCKED"
    if not identity_is_confirmed(evidence.get("certificate_identity")):
        return False, "certificate identity not confirmed (not the literal SAN) in evidence"
    if evidence.get("certificate_identity") != b["identity"]:
        return False, "certificate identity != expected workflow identity"
    if evidence.get("certificate_issuer") != b["issuer"]:
        return False, "certificate issuer != expected OIDC issuer"
    if evidence.get("certificate_audience") != b["audience"]:
        return False, "certificate audience != expected OIDC audience (sigstore)"
    statements = parse_verified_attestation(evidence.get("verified_attestation") or "")
    if not statements:
        return False, "no verified attestation result (discovery alone is not trust)"
    ok, reason = False, "verified statement does not bind"
    for st in statements:
        ok, reason = check_verified_statement(
            st,
            expected_image_ref=evidence.get("image_ref"),
            expected_digest=evidence.get("digest"),
            expected_source_sha=b["source_sha"],
            expected_tools_sha=b["tools_sha"],
            expected_workflow_sha=b["workflow_sha"],
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
    # review #99 item 1 + review #103 item 2: the SPDX attestation is verified
    # for the SAME digest — an unverified SBOM must not slip through while only
    # the SLSA provenance is checked. The two bindings are DISTINCT and both are
    # required, so the predicateType string alone proves neither:
    #   * SBOM→digest  (this SPDX attestation): the signed subject is image@digest
    #     AND the predicate is a non-empty SPDX document of the expected shape.
    #   * digest→source (the SLSA attestation above): the same image@digest is
    #     bound to the pinned source SHA via predicate.materials[].digest.sha1.
    spdx_statements = parse_verified_attestation(evidence.get("spdx_attestation") or "")
    if not spdx_statements:
        return False, "no verified SPDX attestation result (discovery alone is not trust)"
    spdx_ok, spdx_reason = False, "SPDX attestation does not bind image/digest"
    for st in spdx_statements:
        spdx_ok, spdx_reason = check_verified_spdx_statement(
            st,
            expected_image_ref=evidence.get("image_ref"),
            expected_digest=evidence.get("digest"),
        )
        if spdx_ok:
            break
    if not spdx_ok:
        return False, spdx_reason
    return True, "all bindings verified"


# ---------------------------------------------------------------------------
# Lock write (full image + digest as ONE pair, section-aware, preserving the
# rest of the file byte-for-byte)
# ---------------------------------------------------------------------------

def verify_lock_image_agreement(lock_path, image_ref):
    """(ok, reason). The lock's ``image.registry`` (FULL image name) must already
    equal the FULL ``image_ref`` the gate was authorized to release — WITHOUT
    writing anything.

    review #58 item 5: this is the PRE-PUSH pre-agreement check. It is run in the
    release job BEFORE any build/push, so an image/path mismatch (e.g. a template
    IMAGE of ``…/aiopslab/otus-diplom-portal`` against a pinned lock of
    ``ghcr.io/dedvmedved-dot/otus-diplom-portal``) is refused before credentials
    are used, instead of only at apply time. The full image is agreed from the
    policy; the real lock is never modified by this check.
    """
    text = Path(lock_path).read_text()
    lines = text.split("\n")
    img_idx = None
    for i, ln in enumerate(lines):
        if ln.strip() == "image:":
            img_idx = i
            break
    if img_idx is None:
        return False, "lock image: section not found"
    base_indent = len(lines[img_idx]) - len(lines[img_idx].lstrip())
    for i in range(img_idx + 1, len(lines)):
        ln = lines[i]
        if ln.strip() == "":
            continue
        indent = len(ln) - len(ln.lstrip())
        if indent <= base_indent:
            break
        stripped = ln.strip()
        if stripped.startswith("registry:"):
            cur_reg = stripped.split(":", 1)[1].strip().strip('"')
            if cur_reg != image_ref:
                return False, (
                    "lock image registry %r != agreed full image %r "
                    "(pair mismatch; refuse before push)" % (cur_reg, image_ref))
            return True, "lock image pre-agreed (full image matches policy)"
    return False, "lock image registry marker not found"


def _line_spans(raw):
    """Split ``raw`` into ``(start, end)`` byte spans, one per line.

    ``end`` includes the line terminator (``\\n``, ``\\r\\n`` or a lone ``\\r``),
    or equals ``len(raw)`` for a final line that has NO trailing newline. Each
    line's exact original terminator is preserved so mixed / CRLF endings and an
    absent trailing newline are never normalized away.
    """
    spans = []
    i = 0
    n = len(raw)
    while i < n:
        start = i
        while i < n and raw[i:i + 1] not in (b"\n", b"\r"):
            i += 1
        if i < n:
            if raw[i:i + 1] == b"\r":
                i += 1
                if i < n and raw[i:i + 1] == b"\n":
                    i += 1
            else:
                i += 1
        spans.append((start, i))
    return spans


def _line_content(raw, start, end):
    """The line's CONTENT bytes (its terminator stripped)."""
    e = end
    if e > start and raw[e - 1:e] == b"\n":
        e -= 1
        if e > start and raw[e - 1:e] == b"\r":
            e -= 1
    elif e > start and raw[e - 1:e] == b"\r":
        e -= 1
    return raw[start:e]


# Trusted tools checkout root (review #76): the directory holding the pinned
# tools tree — its ROOT images.lock alongside portal/tools/forgejo_lock_gate.py.
# This module lives at <root>/portal/tools/forgejo_lock_gate.py, so the root is
# three levels up from __file__. apply_lock_pair may write ONLY to
# <root>/images.lock; a caller-supplied path is never trusted, only VALIDATED
# against this root (a file outside it, a nested same-named file, or a path
# substituted through a symlink is refused). Offline tests and the workflow may
# pass an explicit tools_root (--tools-root) to point at a scratch checkout.
TRUSTED_TOOLS_ROOT = Path(__file__).resolve().parents[2]


def _has_symlink_component(path):
    """True if ``path`` traverses a symlink in ANY component (file or directory).

    Walks the path component-by-component WITHOUT pre-collapsing ``..``/``.``.
    ``os.path.abspath`` (like ``Path.resolve``) folds ``..`` lexically, which drops
    a symlinked ancestor from the component list BEFORE it is checked — e.g.
    ``root/sub/../images.lock`` where ``sub`` is a symlink is rewritten to
    ``root/images.lock`` and the ``sub`` symlink is never seen. Here ``..`` is
    applied against the path accumulated so far (symlink-free by induction), so a
    symlink is always detected BEFORE a ``..`` could traverse through it. ``.`` is
    a no-op. A component that does not exist yet cannot be a symlink, so a missing
    tail is treated as symlink-free.
    """
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    cur = Path(p.parts[0])
    for part in p.parts[1:]:
        if part in (".", ""):
            continue
        if part == "..":
            cur = cur.parent
            continue
        nxt = cur / part
        try:
            st = os.lstat(nxt)
        except OSError:
            return False
        if stat.S_ISLNK(st.st_mode):
            return True
        cur = nxt
    return False


def apply_lock_pair(lock_path, image_ref, digest, tools_root=None):
    """Update only the canonical Portal record in the platform inventory.

    review #76: the write target is the TRUSTED tools checkout root images.lock,
    NOT the caller-supplied path. ``tools_root`` defaults to this module's own
    checkout root (TRUSTED_TOOLS_ROOT); the lock path is only ever VALIDATED
    against it. A file outside the root, a nested same-named file, or a path
    substituted through a symlink (the file or any ancestor) is refused BEFORE
    any write.

    review #79: the reference path itself is now also verified — the trusted
    root, the trusted ``<root>/images.lock`` reference, and the input path are
    each checked component-by-component (no ``..`` pre-collapse) BEFORE any
    dereference, and the input must be the SAME inode as the ordinary regular
    ``<root>/images.lock``. Only that verified file is read and written.

    review #82: ``os.path.samefile`` proves inode identity, NOT the directory
    entry name. A different name for the same inode (e.g. a hardlink alias)
    still passes ``samefile``, so the read, temp-file directory, ``stat`` and
    ``os.replace`` must all operate on the VERIFIED reference ``trusted``
    (``<root>/images.lock``) — NOT on the caller-supplied ``path``. Operating on
    ``path`` would ``os.replace`` the alias entry and leave the canonical root
    ``images.lock`` unchanged.
    """
    root = Path(tools_root) if tools_root is not None else TRUSTED_TOOLS_ROOT
    path = Path(lock_path)
    # review #79: the TRUSTED reference path and the INPUT path are each verified
    # INDEPENDENTLY, BEFORE dereferencing, without losing components. A
    # ``.resolve()`` equality proves nothing about which symlink the reference
    # itself crossed: if <root>/images.lock (or <root> itself) is a symlink,
    # resolving BOTH paths to the same target would let the write land on the
    # symlink's target instead of the ordinary root file. Check the root, then
    # the reference, then the input — each must be symlink-free — and only then
    # prove (by inode identity, not resolved-string equality) that the input IS
    # that ordinary regular root file.
    if _has_symlink_component(root):
        raise RuntimeError("tools checkout root must not traverse a symlink")
    trusted = root / "images.lock"
    if _has_symlink_component(trusted):
        raise RuntimeError("images.lock reference path must not traverse a symlink")
    if _has_symlink_component(path):
        raise RuntimeError("images.lock path must not traverse a symlink")
    try:
        same = os.path.samefile(str(path), str(trusted))
    except OSError:
        same = False
    if not same:
        raise RuntimeError("images.lock is not the trusted tools checkout root images.lock")
    if not trusted.is_file():
        raise RuntimeError("images.lock is not an ordinary regular file in the checkout root")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError("invalid digest")
    # review #82: from here on, every file operation targets the VERIFIED
    # reference `trusted`, never the caller-supplied `path` (samefile identity is
    # not a directory-entry-name guarantee — a hardlink alias shares the inode but
    # is a different name, and replacing THAT name leaves root images.lock stale).
    raw = trusted.read_bytes()
    lines = raw.splitlines(keepends=True)
    in_images = False
    seen = False
    records = []
    for i, line in enumerate(lines):
        text = line.rstrip(b"\r\n")
        if not text.strip() or text.lstrip().startswith(b"#"):
            continue
        if text == b"images:":
            if seen:
                raise RuntimeError("duplicate images section")
            in_images = seen = True
        elif not text.startswith(b" "):
            in_images = False
        elif in_images:
            # Fail closed on noncanonical YAML (aliases, duplicate keys, etc.).
            m = re.fullmatch(rb"  - component: ([a-z0-9-]+)", text)
            if m:
                records.append((m[1], {}))
                continue
            m = re.fullmatch(rb'    ([a-z_]+): (?:"([^"\\]*)"|([A-Za-z0-9_./:-]+))', text)
            if not m or not records or m[1] in records[-1][1]:
                raise RuntimeError("ambiguous images.lock record")
            fields = records[-1][1]
            fields[m[1]] = (m[2] if m[2] is not None else m[3], i)
    targets = [fields for name, fields in records if name == b"otus-diplom-portal"]
    if len(targets) != 1:
        raise RuntimeError("expected exactly one Portal record")
    fields = targets[0]
    expected = image_ref.encode()
    if (fields.get(b"image", (None,))[0] != expected or
            sum(f.get(b"image", (None,))[0] == expected for _, f in records) != 1):
        raise RuntimeError("pair mismatch or duplicate image")
    for key, marker, replacement in ((b"digest", b"NOT_VERIFIED", digest.encode()),
                                     (b"verified", b"false", b"true")):
        if fields.get(key, (None,))[0] != marker:
            raise RuntimeError("lock digest already set or invalid verification state")
        i = fields[key][1]
        if key == b"verified" and lines[i].rstrip(b"\r\n") != b"    verified: false":
            raise RuntimeError("invalid verified boolean")
        lines[i] = lines[i].replace(marker, replacement, 1)
    with tempfile.NamedTemporaryFile(dir=trusted.parent, delete=False) as tmp:
        try:
            tmp.write(b"".join(lines))
            tmp.flush()
            os.fchmod(tmp.fileno(), trusted.stat().st_mode & 0o777)
            os.replace(tmp.name, trusted)
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

USAGE = """usage:
  forgejo_lock_gate.py owner-gate <gate.json> --pinned-source <sha> --pinned-tools <sha>
      --pinned-workflow <sha> --package <image_ref> [--owner O --repository R --ref F
      --actor A --run-id RID --run-attempt 1
      --observed-repository R --observed-ref F --observed-workflow-sha W]
  forgejo_lock_gate.py inventory --source-inventory <paths.txt> --tools-inventory <paths.txt>
      --pinned-source <sha> --pinned-tools <sha> [--source-tree-sha256 <64hex>]
  forgejo_lock_gate.py lock-image-check --lock <versions.lock> --image <full_image_ref>
  forgejo_lock_gate.py registry-fetch --allowed-registry <host> --image-ref <ref> --digest <sha256:..>
      --manifest-out <file> --dcd-out <file>
  forgejo_lock_gate.py digest <build-metadata.json>
  forgejo_lock_gate.py predicate <source_sha> <workflow_sha> <tools_sha> <run_id>
  forgejo_lock_gate.py workflow-blob --workflow-dir <dir> --commit <sha> --path <workflow_file>
  forgejo_lock_gate.py tools-pin-check --tools-dir <dir>
  forgejo_lock_gate.py verify <evidence.json> [--apply <lock_file> --apply-lock true
      --tools-root <dir>] [--oidc-trust-confirmed true]"""


def _load_evidence(path):
    """Load an evidence bundle; ``manifest_file`` / ``verified_attestation_file`` /
    ``spdx_attestation_file`` (paths) are read into ``manifest_bytes`` /
    ``verified_attestation`` / ``spdx_attestation``."""
    ev = json.loads(Path(path).read_text())
    if "manifest_file" in ev:
        ev["manifest_bytes"] = Path(ev.pop("manifest_file")).read_bytes()
    if "verified_attestation_file" in ev:
        ev["verified_attestation"] = Path(ev.pop("verified_attestation_file")).read_text()
    if "spdx_attestation_file" in ev:
        ev["spdx_attestation"] = Path(ev.pop("spdx_attestation_file")).read_text()
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
        # review #61 item 1: --pinned-workflow is REQUIRED and must be the
        # INDEPENDENT protected out-of-band policy pin (a repo secret supplied by
        # the Owner, SEPARATE from the owner gate document). There is NO fallback
        # to the document's own workflow_sha — that would collapse the policy pin
        # and the document into one quantity and reduce the check to two values
        # (document vs runtime) instead of three. An absent/invalid pin stops the
        # preflight fail-closed BEFORE any release rights are granted.
        pinned_workflow = flag("--pinned-workflow")
        if not valid_sha(pinned_workflow):
            print("OWNER GATE NOT VERIFIED: --pinned-workflow (independent workflow "
                  "SHA policy pin) missing/invalid", file=sys.stderr)
            return 1
        ok, reason = verify_owner_gate(
            gate,
            expected_owner=flag("--owner", EXPECTED_OWNER),
            expected_source_sha=flag("--pinned-source", ""),
            expected_tools_sha=flag("--pinned-tools", ""),
            expected_workflow_sha=pinned_workflow,
            expected_repository=flag("--repository", FORGEJO_REPO),
            expected_package=flag("--package", ""),
            expected_ref=flag("--ref", REF),
            actor=flag("--actor"),
            run_id=flag("--run-id"),
            run_attempt=flag("--run-attempt", "1"),
            observed_repository=flag("--observed-repository"),
            observed_ref=flag("--observed-ref"),
            observed_workflow_sha=flag("--observed-workflow-sha"),
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
            tools_pin=flag("--pinned-tools", ""),
            source_tree_sha256=flag("--source-tree-sha256"),
        )
        print(json.dumps({"inventory": ok, "reason": reason}))
        return 0 if ok else 1

    if mode == "lock-image-check":
        lock_path = flag("--lock")
        image_ref = flag("--image")
        if not lock_path or not image_ref:
            print(USAGE, file=sys.stderr)
            return 2
        ok, reason = verify_lock_image_agreement(lock_path, image_ref)
        print(json.dumps({"lock_image_agreed": ok, "reason": reason}))
        if not ok:
            print("LOCK IMAGE NOT AGREED: " + reason, file=sys.stderr)
            return 1
        return 0

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
        # Verify bytes + Docker-Content-Digest at FETCH time (BEFORE any
        # sign/attest or lock), not deferred to just before the lock.
        ok, reason = verify_registry_manifest(allowed, allowed, image_ref, digest, body, dcd)
        if not ok:
            print("REGISTRY NOT VERIFIED: %s" % reason, file=sys.stderr)
            return 1
        Path(flag("--manifest-out", "")).write_bytes(body)
        Path(flag("--dcd-out", "")).write_text(dcd or "")
        print(json.dumps({"registry": allowed, "digest": digest,
                          "dockerContentDigest": dcd, "bytes": len(body)}))
        return 0

    if mode == "predicate":
        if len(args) != 4:
            print(USAGE, file=sys.stderr)
            return 2
        print(json.dumps(build_predicate(args[0], args[1], args[2], args[3]), sort_keys=True))
        return 0

    if mode == "workflow-blob":
        blob, reason = observe_workflow_blob(
            flag("--workflow-dir", ""), flag("--commit", ""), flag("--path", ""))
        if blob is None:
            print("WORKFLOW BLOB NOT OBSERVED: " + reason, file=sys.stderr)
            return 1
        print(blob)
        return 0

    if mode == "tools-pin-check":
        ok, reason = verify_tools_pin(flag("--tools-dir", ""))
        print(json.dumps({"tools_pin": ok, "reason": reason}))
        if not ok:
            print("TOOLS PIN NOT VERIFIED: " + reason, file=sys.stderr)
            return 1
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
                              ("audience", "--audience"),
                              ("repository", "--repository"), ("ref", "--ref"),
                              ("workflow_file", "--workflow-file"),
                              ("build_type", "--build-type"),
                              ("source_sha", "--pinned-source"),
                              ("tools_sha", "--pinned-tools"),
                              ("workflow_sha", "--workflow-sha"),
                              ("source_tree_sha256", "--source-tree-sha256")):
            val = flag(flagname)
            if val is not None:
                bindings[key] = val
        # review #95 item 2 (B): the keyless (OIDC) trust confirmation is a
        # boolean flag defaulting to false — an absent or non-"true" value keeps
        # the release BLOCKED. It is only ever "true" when the workflow's
        # inputs.oidc_trust_confirmed == true.
        oidc_val = flag("--oidc-trust-confirmed")
        if oidc_val is not None:
            bindings["oidc_trust_confirmed"] = (oidc_val == "true")
        allowed, reason = decide_lock_update(evidence, bindings or None)
        print(json.dumps({"allowed": allowed, "reason": reason}))
        if not allowed:
            print("LOCK UPDATE NOT ALLOWED: " + reason, file=sys.stderr)
            return 1
        apply_path = flag("--apply")
        if apply_path:
            # Writing the lock requires an EXPLICIT owner authorization
            # (--apply-lock true == inputs.apply_lock == true). Without it the
            # check-only result is emitted but nothing is written.
            if flag("--apply-lock") != "true":
                print("LOCK UPDATE NOT ALLOWED: --apply requires --apply-lock true", file=sys.stderr)
                return 1
            try:
                # review #76: the write is bound to the TRUSTED tools checkout
                # root (--tools-root), never to the caller-supplied --apply path
                # alone. Without --tools-root the module's own checkout root is
                # used (fail-closed for any --apply path outside it).
                apply_lock_pair(apply_path, evidence["image_ref"], evidence["digest"],
                                tools_root=flag("--tools-root"))
                print("LOCK UPDATED: %s -> image=%s digest=%s" % (
                    apply_path, evidence["image_ref"], evidence["digest"]))
            except Exception as exc:
                print("LOCK UPDATE NOT ALLOWED: apply failed: %s" % exc, file=sys.stderr)
                return 1
        return 0

    print("unknown mode: " + mode, file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
