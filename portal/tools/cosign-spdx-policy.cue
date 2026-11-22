// cosign verify-attestation --policy source-binding policy for the SPDX (JSON)
// attestation. The SPDX SBOM document describes the exact image it is attached
// to, so its source binding IS the signed subject (image@digest). This policy
// asserts the SPDX predicateType and a present subject; the subject digest
// itself is verified by cosign from the positional image@digest argument and by
// check_verified_spdx_statement in forgejo_lock_gate.py.
predicateType: "https://spdx.dev/Document"

subject: [...]
