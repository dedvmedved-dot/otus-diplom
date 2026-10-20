G1 stack decisions (from task):
- Go 1.27.3 (downloaded + SHA256 65efbc80... verified on build host).
- k8s.io client-go/api/apimachinery v0.36.2; pgx/v5 v5.11.0 (pgxpool).
- modular monolith: cmd/portal + internal/{httpapi,collectors,store,health,auth,config,model} + web + migrations.
- native ES modules + CSS frontend; no framework/CDN.
- OCI FROM scratch, static binary, UID/GID 65532.
- No os/exec in runtime packages (static check: none present).
