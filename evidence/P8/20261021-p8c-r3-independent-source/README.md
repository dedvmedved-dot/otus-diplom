# Evidence navigation / reproduction

Start with `result.md`, then `closure-matrix.md`. Exact tested source is `817f0ecef8da1cd756f4b6ab48d61e023764329a`, all66 Portal blob hashes in `source-index.json`. The evidence-only child does not alter application source.

- `commands.json`: final run command/cwd/UTC/exits for checks01–18; logs19–20 include their own command/time/exits.
- `raw-transcript.txt`: concatenation of all20 actual logs, not PASS summaries.
- `harness/`: exact transient orchestration scripts used for this execution, retaining original workspace paths for audit. They are not application dependencies.
- `reproduce.py`: portable source-only runner. With a checkout containing this evidence, install the checksum-verified Go toolchain using the source script, place it on PATH, and run `npm ci --ignore-scripts` in `portal`. Then run `python3 evidence/P8/20261021-p8c-r3-independent-source/reproduce.py`. It checks every source blob before execution. No cluster/Owner/workflow operation is included.
- Native SQL follow-up: on the existing authorized isolated PG17 host, supply its local test URL through the approved local mechanism and use `reproduce.py --native-pg` or the exact tagged Go command in result.md. The suite rejects non-test destinations. Do not paste URLs/credentials into evidence.
- Optional compatibility reproduction: `npm ci --ignore-scripts` inside this evidence's `wasm-sql/`, then `reproduce.py --wasm-compat`. This uses only a loopback ephemeral WASM PostgreSQL engine, one connection and exec query mode. It is explicitly not nativePG/TLS/HA qualification. Package versions and npm integrity lock are included; node_modules are not.
- `cosign-offline/`: pinned Go module and actual synthetic generated Statement. `go run . predicate.json` in that directory invokes the actual Cosign v3.1.3 GenerateStatement library. No key/sign/upload/network identity operation is performed; initial module download uses ordinary public Go module verification. `17`/`18` logs show actual generation followed by the strict release payload checker. Synthetic source/digest are fixtures, not provenance for a released image.
- Public release/action/Go/test-image metadata evidence does not claim tools executed in CI. The application image digest, final-image scan/SBOM/signatures/private visibility remain NOT_EXECUTED.

The read-only NetPol inventory script is source-prepared but was not executed. `environment-limitations.json` records the concrete local limitations. Historical evidence remains untouched. Tests use synthetic API objects and credentials only; no production secret, token, TLS key or live kubeconfig is contained here.
