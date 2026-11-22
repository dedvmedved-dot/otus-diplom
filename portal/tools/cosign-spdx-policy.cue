// cosign verify-attestation --policy source-binding policy for the SPDX (JSON)
// attestation. The SPDX SBOM document describes the exact image it is attached
// to, so its source binding IS the signed subject (image@digest); the subject
// digest itself is verified by cosign from the positional image@digest argument
// and by check_verified_spdx_statement in forgejo_lock_gate.py.
//
// review #103 item 2: this policy must require a SIGNED NON-EMPTY SPDX document
// of the expected shape — NOT just the predicateType and a subject list. The
// predicate must carry the SPDX document identity (SPDX-2.x + SPDXRef-DOCUMENT),
// a non-empty name / documentNamespace and a NON-EMPTY packages list. A
// missing / empty / foreign predicate is rejected here (cuejson.Validate)
// before the gate re-checks the same shape over the SIGNED statement.
predicateType: "https://spdx.dev/Document"

predicate: {
	spdxVersion: =~"^SPDX-2\\.[0-9]+$"
	SPDXID: "SPDXRef-DOCUMENT"
	name: =~"^.+$"
	documentNamespace: =~"^.+$"
	packages: [_, ...]
}

subject: [...]
