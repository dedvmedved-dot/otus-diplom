#!/usr/bin/env python3
"""GATE-layer half of the SPDX per-layer matrix (review #106 item 2).

Runs the REAL gate validator ``check_verified_spdx_statement`` over the SAME SPDX
statement cases the ``cue-validation`` Go matrix exercises on the CUE layer. The
CUE layer (cosign ``--policy`` = cuejson.Validate with cue.Final()) rejects only
CONTRADICTIONS on PRESENT fields; ABSENCE/EMPTINESS is this layer's job. This
script therefore expects:

    * ACCEPT — only the valid Syft/cosign SPDX document;
    * REJECT — foreign predicateType / spdxVersion / SPDXID / empty packages
      (contradictions on present fields, ALSO caught by CUE), AND
    * REJECT — missing/empty predicate, missing name / documentNamespace /
      packages (caught ONLY here, not by CUE).

Offline, synthetic inputs only; imports the SAME ``forgejo_lock_gate`` module the
workflow drives (one validation implementation).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "portal" / "tools"))

import forgejo_lock_gate as gate  # noqa: E402

IMAGE = "registry.example/aiopslab/otus-diplom-portal"
DIGEST = "sha256:" + hashlib.sha256(
    b'{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}'
).hexdigest()


def _stmt(**kw):
    predicate = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "otus-diplom-portal",
        "documentNamespace": "https://anchore.com/syft/otus-diplom-portal-0.1.0",
        "creationInfo": {
            "licenseListVersion": "3.24",
            "creators": ["Organization: Anchore, Inc", "Tool: syft-1.55.0"],
            "created": "2026-01-01T00:00:00Z",
        },
        "packages": [
            {"SPDXID": "SPDXRef-Package-portal", "name": "portal",
             "versionInfo": "0.1.0", "downloadLocation": "NOASSERTION",
             "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION",
             "copyrightText": "NOASSERTION"},
        ],
        "documentDescribes": ["SPDXRef-Package-portal"],
    }
    stmt = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": IMAGE, "digest": {"sha256": DIGEST[len("sha256:"):]}}],
        "predicateType": gate.SPDX,
        "predicate": predicate,
    }
    for k, v in kw.items():
        if v is _DROP:
            stmt.pop(k)
        else:
            stmt[k] = v
    return stmt


class _Drop:
    pass


_DROP = _Drop()


def _run(name, stmt, want):
    allowed, reason = gate.check_verified_spdx_statement(
        stmt, expected_image_ref=IMAGE, expected_digest=DIGEST)
    got = "ACCEPT" if allowed else "REJECT"
    ok = (allowed == want)
    print("%-32s gate=%s  want=%s  %s%s" % (
        name, got, "ACCEPT" if want else "REJECT",
        "OK" if ok else "FAIL", "" if ok else "  (reason=%s)" % reason))
    return ok


def main():
    cases = []
    # Contradictions on PRESENT fields — ALSO caught by the CUE layer.
    cases.append(("spdx valid (syft shape)", _stmt(), True))
    cases.append(("spdx wrong predicateType", _stmt(predicateType=gate.SLSA), False))
    cases.append(("spdx wrong spdxVersion (foreign)",
                  _stmt(predicate={**_stmt()["predicate"], "spdxVersion": "SPDX-1.0"}), False))
    cases.append(("spdx wrong SPDXID (foreign)",
                  _stmt(predicate={**_stmt()["predicate"], "SPDXID": "SPDXRef-SomethingElse"}), False))
    cases.append(("spdx empty packages (foreign)",
                  _stmt(predicate={**_stmt()["predicate"], "packages": []}), False))
    # Absence/emptiness — caught ONLY by the gate (CUE layer ACCEPTS these).
    cases.append(("spdx missing predicate", _stmt(predicate=_DROP), False))
    cases.append(("spdx empty predicate {}", _stmt(predicate={}), False))
    base = _stmt()["predicate"]
    cases.append(("spdx missing name",
                  _stmt(predicate={k: v for k, v in base.items() if k != "name"}), False))
    cases.append(("spdx missing documentNamespace",
                  _stmt(predicate={k: v for k, v in base.items() if k != "documentNamespace"}), False))
    cases.append(("spdx missing packages",
                  _stmt(predicate={k: v for k, v in base.items() if k != "packages"}), False))

    fail = False
    for name, stmt, want in cases:
        if not _run(name, stmt, want):
            fail = True
    print()
    if fail:
        print("GATE LAYER MATRIX: MISMATCH", file=sys.stderr)
        return 1
    print("GATE LAYER MATRIX: ALL CASES MATCHED EXPECTATION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
