# Данные владельца для допуска B — OIDC + admission-барьер (2026-11-24)

По PR #113 / наряду #112 (BLOCKED — NOT_READY_FOR_DISPATCH).

## OIDC
- issuer: `https://git.aiopslab.online/api/actions`
- trust roots (jwks_uri): `https://git.aiopslab.online/api/actions/.well-known/keys` (RS256)
- subject (SAN / certificate identity): `repo:aiopslab/otus-diplom:ref:refs/heads/<branch>:<event>`

## Admission-барьер
- runner label `otus-diplom-admission` добавлен на runner `otus-diplom` (VM112 10.129.10.62, forgejo-runner v6.1.0).
- runner переподключён: labels [linux amd64 otus-diplom self-hosted otus-diplom-admission], declared successfully.
