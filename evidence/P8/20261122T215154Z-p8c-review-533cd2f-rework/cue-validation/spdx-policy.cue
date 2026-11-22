// cosign verify-attestation --policy source-binding policy for the SPDX (JSON)
// attestation. The SPDX SBOM document describes the exact image it is attached
// to, so its source binding IS the signed subject (image@digest); the subject
// digest itself is verified by cosign from the positional image@digest argument
// and by check_verified_spdx_statement in forgejo_lock_gate.py.
//
// review #103 item 2 + review #106 item 2: this policy constrains the SHAPE of a
// SIGNED SPDX document on the fields that ARE PRESENT — predicateType must be
// the SPDX Document type, the predicate must carry the SPDX document identity
// (SPDX-2.x + SPDXRef-DOCUMENT), a non-empty name / documentNamespace and a
// NON-EMPTY packages list. cosign's `--policy` runs cuejson.Validate with
// cue.Final(), which rejects CONTRADICTIONS on PRESENT fields (a foreign
// predicateType, a wrong spdxVersion/SPDXID, an empty packages list) but does
// NOT require ABSENT fields. Absence/emptiness of the predicate itself, name or
// documentNamespace is therefore the GATE's responsibility — it is rejected by
// check_verified_spdx_statement() in forgejo_lock_gate.py over the SIGNED
// statement (see test_owner_gate_barrier.py:TestSpdxAttestation and the
// per-layer matrix in evidence/), NOT by this policy.
predicateType: "https://spdx.dev/Document"

predicate: {
	spdxVersion: =~"^SPDX-2\\.[0-9]+$"
	SPDXID: "SPDXRef-DOCUMENT"
	name: =~"^.+$"
	documentNamespace: =~"^.+$"
	packages: [_, ...]
}

subject: [...]
