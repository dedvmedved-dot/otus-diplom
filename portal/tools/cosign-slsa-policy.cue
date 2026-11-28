// cosign verify-attestation --policy source-binding policy for the SLSA
// provenance attestation. Validates the SIGNED in-toto statement the same way
// cosign does (cuejson.Validate): predicateType must be SLSA v0.2 and the
// pinned SOURCE SHA must be bound as the FIRST material digest. This is the
// source binding that the removed `-a ref=<sha>` flag tried to express through
// an unsupported mechanism — cosign verify-attestation v3.1.3 rejects `-a`
// ("unknown shorthand flag: 'a'"). Subject/digest is verified by cosign from the
// positional image@digest argument; the full set-membership source binding is
// additionally enforced by check_verified_statement in forgejo_lock_gate.py.
//
// Keep sourceSHA in sync with PINNED_SOURCE_SHA (env + gate constant). A
// mismatch is a fail-closed policy failure at verify-attestation time.
sourceSHA: "4c09d6b4a85e2d021516244988f48b92eade7acf"

predicateType: "https://slsa.dev/provenance/v0.2"

predicate: {
	materials: [
		{
			digest: {
				sha1: sourceSHA
			}
		},
		...,
	]
}
