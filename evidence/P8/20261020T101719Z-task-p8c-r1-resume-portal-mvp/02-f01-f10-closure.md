F01-F10 closure (all fixed, build/vet/test/race green):
- F01/F07: projected serviceAccountToken (expirationSeconds=3600, API CA, namespace downwardAPI); DB password + auth verifier via secretKeyRef env; fixed DB identity (host/port/name/user/ssl). Migrator gets no token.
- F02/F09: all 11 endpoints match openapi.json (envelope/Source/Warning/Condition/Error enums, additionalProperties=false semantics); cursor snapshot-bound (CURSOR_EXPIRED); continue handling + cap 200/500 + partial flags; unknown query keys -> 400; 404/405 JSON with Allow.
- F03/F06: per-source registry (state ok/error/unsupported, errorCode); node health from Ready+pressure; VolumeSnapshot readyToUse boolean; named GETs (portal-db-daily, portal-db-backup, portal-gateway); EndpointSlice ready endpoints; node/pod metrics quantities+timestamp+window; Barman 3 families -> API/UI.
- F04/F05: persistence wired (bounded batch + Kubernetes Events dedup + prune); Prune via PG17 CTE (TTL OR over-cap, <=1000/batch); dedup_key returned as TimelineEvent.id; ListEvents nullable-safe.
- F08: transport guard (GET/HEAD only, fixed API host, no redirects); fixed error codes (no raw err.Error()); http.Server Read/Write/Idle/MaxHeader timeouts; management 8081 not in Service.
- F10: actual outputs recorded (build/vet/test/race exit codes below).
