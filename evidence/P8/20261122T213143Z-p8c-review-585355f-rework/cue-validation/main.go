package main

import (
	"fmt"
	"os"

	"cuelang.org/go/cue/cuecontext"
	"cuelang.org/go/cue/load"
	cuejson "cuelang.org/go/encoding/json"
)

func validate(jsonBody string, entrypoints []string) error {
	ctx := cuecontext.New()
	bis := load.Instances(entrypoints, nil)
	for _, bi := range bis {
		if bi.Err != nil {
			return bi.Err
		}
		value := ctx.BuildInstance(bi)
		if value.Err() != nil {
			return value.Err()
		}
		if err := cuejson.Validate([]byte(jsonBody), value); err != nil {
			return err
		}
	}
	return nil
}

const src = "4c09d6b4a85e2d021516244988f48b92eade7acf"
const tools = "1111111111111111111111111111111111111111"
const wf = "2222222222222222222222222222222222222222"
const digest = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
const img = "git.aiopslab.online/aiopslab/otus-diplom-portal"

func stmt(predicateType, predicateJSON string) string {
	return fmt.Sprintf(`{
  "_type": "https://in-toto.io/Statement/v0.1",
  "predicateType": %q,
  "subject": [{"name": %q, "digest": {"sha256": %q}}],
  "predicate": %s
}`, predicateType, img, digest, predicateJSON)
}

func slsaPred(sourceMaterial string) string {
	return fmt.Sprintf(`{
    "builder": {"id": "<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>"},
    "buildType": "https://forgejo.org/Attestations/ForgejoActionsWorkflow@v1",
    "invocation": {"configSource": {"uri": "git+https://git.aiopslab.online/aiopslab/otus-diplom@refs/heads/main", "digest": {"sha1": %q}, "entryPoint": ".forgejo/workflows/p8c-portal-forgejo-release.yml"}},
    "materials": [
      {"uri": "git+https://git.aiopslab.online/aiopslab/otus-diplom@refs/heads/main", "digest": {"sha1": %q}},
      {"uri": "git+https://git.aiopslab.online/aiopslab/otus-diplom@refs/heads/main", "digest": {"sha1": %q}}
    ],
    "metadata": {"buildInvocationId": "1234567890"}
  }`, wf, sourceMaterial, tools)
}

// Realistic Syft/cosign SPDX-2.3 document with a NON-EMPTY packages list.
func spdxPred() string {
	return `{
    "spdxVersion": "SPDX-2.3",
    "dataLicense": "CC0-1.0",
    "SPDXID": "SPDXRef-DOCUMENT",
    "name": "otus-diplom-portal",
    "documentNamespace": "https://anchore.com/syft/otus-diplom-portal-0.1.0",
    "creationInfo": {"licenseListVersion": "3.24", "creators": ["Organization: Anchore, Inc", "Tool: syft-1.55.0"], "created": "2026-01-01T00:00:00Z"},
    "packages": [{"SPDXID": "SPDXRef-Package-portal", "name": "portal", "versionInfo": "0.1.0", "downloadLocation": "NOASSERTION", "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION", "copyrightText": "NOASSERTION"}],
    "documentDescribes": ["SPDXRef-Package-portal"]
  }`
}

func main() {
	slsaPolicy := []string{"slsa-policy.cue"}
	spdxPolicy := []string{"spdx-policy.cue"}

	// NOTE on the split between the two layers (review #103 item 2):
	//   * cosign's `--policy` runs cuejson.Validate, which calls
	//     v.Validate(cue.Final()) — it rejects CONTRADICTIONS on PRESENT fields
	//     (wrong predicateType, wrong spdxVersion/SPDXID, empty packages) but
	//     does NOT require absent fields (cue.Final, not cue.Concrete).
	//   * The GATE (check_verified_spdx_statement) enforces ABSENCE/EMPTINESS —
	//     missing/empty predicate, missing name/documentNamespace, empty packages —
	//     over the signed statement (see test_owner_gate_barrier.py).
	cases := []struct {
		name string
		json string
		pol  []string
		want bool
	}{
		// SLSA provenance (unchanged policy)
		{"slsa valid (source bound)", stmt("https://slsa.dev/provenance/v0.2", slsaPred(src)), slsaPolicy, true},
		{"slsa wrong source material", stmt("https://slsa.dev/provenance/v0.2", slsaPred("3333333333333333333333333333333333333333")), slsaPolicy, false},
		{"slsa wrong predicateType", stmt("https://spdx.dev/Document", slsaPred(src)), slsaPolicy, false},
		// SPDX (review #103 item 2): the policy now constrains the document shape.
		{"spdx valid (syft shape)", stmt("https://spdx.dev/Document", spdxPred()), spdxPolicy, true},
		{"spdx wrong predicateType", stmt("https://slsa.dev/provenance/v0.2", spdxPred()), spdxPolicy, false},
		{"spdx wrong spdxVersion (foreign)", stmt("https://spdx.dev/Document", `{"spdxVersion": "SPDX-1.0", "SPDXID": "SPDXRef-DOCUMENT", "name": "x", "documentNamespace": "https://e/x", "packages": [{"SPDXID": "SPDXRef-Package-1", "name": "p"}]}`), spdxPolicy, false},
		{"spdx wrong SPDXID (foreign)", stmt("https://spdx.dev/Document", `{"spdxVersion": "SPDX-2.3", "SPDXID": "SPDXRef-SomethingElse", "name": "x", "documentNamespace": "https://e/x", "packages": [{"SPDXID": "SPDXRef-Package-1", "name": "p"}]}`), spdxPolicy, false},
		{"spdx empty packages (foreign)", stmt("https://spdx.dev/Document", `{"spdxVersion": "SPDX-2.3", "SPDXID": "SPDXRef-DOCUMENT", "name": "x", "documentNamespace": "https://e/x", "packages": []}`), spdxPolicy, false},
	}

	fail := false
	for _, c := range cases {
		err := validate(c.json, c.pol)
		got := err == nil
		status := "PASS"
		if got != c.want {
			status = "FAIL"
			fail = true
		}
		fmt.Printf("%-32s want=%v got=%v %s", c.name, c.want, got, status)
		if err != nil && c.want {
			fmt.Printf("  (err: %v)", err)
		}
		fmt.Println()
	}
	fmt.Println()
	fmt.Println("GATE-enforced (check_verified_spdx_statement, NOT the CUE layer):")
	fmt.Println("  missing predicate / empty predicate / missing name / missing")
	fmt.Println("  documentNamespace / empty packages are rejected by the gate over the")
	fmt.Println("  SIGNED statement (test_owner_gate_barrier.py:TestSpdxAttestation).")
	if fail {
		os.Exit(1)
	}
	fmt.Println("CUE POLICY VALIDATION: ALL CASES MATCHED EXPECTATION")
}
