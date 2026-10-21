# P8C Portal MVP

Read-only operator console: User → Envoy Gateway → Portal UI/API → PostgreSQL +
read-only Kubernetes APIs.

## Stack

| Layer | Choice |
|---|---|
| Backend | Go 1.27.3, `net/http` ServeMux, `html/template`, `embed` |
| Kubernetes | client-go / api / apimachinery v0.36.2 (typed + dynamic) |
| DB | pgx/v5 v5.11.0 + pgxpool (verify-full) |
| Frontend | native ES modules + CSS (no framework/CDN) |
| Image | own OCI `FROM scratch`, static binary, UID/GID 65532 |

## Layout

- `cmd/portal` — entry point (`serve` default, `migrate` applies schema)
- `internal/config` — env + mount-projection config
- `internal/auth` — Basic Auth (SHA-256 verifier, constant-time)
- `internal/collectors` — read-only K8s + Barman metrics polling (Get/List only)
- `internal/store` — pgxpool persistence + migration ledger + prune
- `internal/model` — sanitized DTOs (no raw K8s objects / env / secret refs)
- `internal/httpapi` — GET/HEAD API + static UI + security headers
- `migrations` — versioned forward-only schema (embedded, SHA-256 checksum)
- `web` — frontend assets (embedded)
- `manifests` — RBAC / Deployment / Service / Gateway / TLS

## Build

```text
make build      # static linux/amd64 binary
make test       # go test ./...
make vet        # go vet ./...
```

## Security

- No `os/exec` in runtime packages; no subprocesses; no shell/kubectl.
- Only GET/HEAD; fixed GVRs; no generic proxy; no write endpoints.
- RBAC allowlist (get/list only); no Secret API, no logs/exec/attach/proxy.
- TLS verify-full to PostgreSQL; dedicated namespaced UI demo CA (cert-manager).
- No secrets in Git/evidence; auth via SHA-256 verifier, constant-time compare.


## RESUME-R3 source corrections (runtime still gated)

Events use a bounded, immutable process-local view of one SQL SELECT (up to 500
rows, 32 views, TTL90s). Values and filter membership cannot shift on upsert,
insert or retention cleanup. Cursor binds snapshot, all filters, backend and
view ID; eviction/restart/source/backend change returns CURSOR_EXPIRED. Partial
is set at the cap and for memory fallback. No long-lived database transaction.

Persistence retains up to16 normalized batches, 500 events and64 status events;
retries idempotently through the same production writer path. Only changes in
platform/persistence/retention state emit transitions. Discarding history latches
dataLoss for the process lifetime; a later write does not erase the loss. Pending
status events are visible in the memory fallback and flushed after recovery.
Lag is computed at response time; never-successful persistence is null.

Run `bash tools/test-dataflow.sh` after `npm ci --ignore-scripts` for the real
collector -> handler (all11 OpenAPI schemas) -> DOM synthetic dataflow test.
No live cluster is used. `go test ./networkpolicy` validates candidate flow union,
NOT the missing live inventory or CNI DNAT behavior. See networkpolicy/PLAN.md.

Release template requires a PREEXISTING private GHCR package linked to this
repository and workflow GITHUB_TOKEN access. Metadata is checked before and after
push; a missing/inaccessible/public package fails closed. Owner establishes the
prerequisite separately after review. No Owner workflow token is consumed.
The template installs the checksum-verified Go archive for build/test with
GOTOOLCHAIN=local. Only release has packages/id-token write. It checks immutable
registry bytes and exact subject/source inside cryptographically verified
signature/attestation output and retains scans/verification artifacts.

Real helpers, workflow publication/dispatch, live policies and production
migration/deployment still need their explicit later gates. Source tests confer
no runtime approval or FINAL ACCEPTED status.
