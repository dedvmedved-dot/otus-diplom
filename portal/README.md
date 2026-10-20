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
