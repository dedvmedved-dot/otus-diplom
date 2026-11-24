# P8C #118 — подготовка первого B: tools SHA зафиксирован, SAN/trust не подтверждены

Роль: Implementation Engineer (Hermes). Наряд — [issue #118](https://git.aiopslab.online/aiopslab/otus-diplom/issues/118),
решение архитектора [#116](https://git.aiopslab.online/aiopslab/otus-diplom/issues/116)
(`docs/architecture/P8C_DECISION_116.md`). Ветка — `engineer/118-prepare-first-b`,
база — `engineer/101-cosign-verify-attestation-gate` (tip `46e77bc…`, PR #102).

## Статус

`PREPARED_PARTIAL — NOT_READY_FOR_DISPATCH`. Один B с `apply_lock=false` разрешён
владельцем, но точный SAN/audience/trust-цепочка владельцем НЕ подтверждены.
`PINNED_TOOLS_SHA` зафиксирован, `WORKFLOW_IDENTITY` остаётся плейсхолдером.

## Что сделано (по вердикту #116)

1. **`PINNED_TOOLS_SHA` зафиксирован** вместо `<FORGEJO_TOOLS_SHA>`: точный tools
   SHA = `46e77bc9a31e43c333b73337bd928bc424e046b8` (tip инструментальной ветки
   `engineer/101-cosign-verify-attestation-gate`, несёт `workflow-blob` +
   `tools-pin-check` + обе CUE-политики). Плейсхолдер заменён в неактивном шаблоне
   `portal/tools/p8c-portal-forgejo-release.yml.template`.
2. **Blob финального неактивного шаблона** (после фиксации tools SHA):
   `96237e87a3be7bba7e9fb74d802397b8119763ab` (объект — blob,
   `git hash-object portal/tools/p8c-portal-forgejo-release.yml.template`).
3. **`WORKFLOW_IDENTITY` / SAN не подтверждён** — остаётся плейсхолдером
   `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` (и в шаблоне, и в `forgejo_lock_gate.py`
   `WORKFLOW_IDENTITY = WORKFLOW_IDENTITY_PLACEHOLDER`). Не угадывается.

## Офлайн-проверки (результаты)

| Проверка | Результат |
|---|---|
| OIDC discovery issuer == `OIDC_ISSUER` шаблона | **СОВПАДАЕТ** — `https://git.aiopslab.online/api/actions` (live `/.well-known/openid-configuration`, файл `evidence/P8/*-p8c-prep-b-118/oidc-discovery.json`) |
| `jwks_uri` + алгоритм | **СОВПАДАЕТ** — `https://git.aiopslab.online/api/actions/.well-known/keys`, `RS256`, 1 ключ (`kty=RSA`, `use=sig`; файл `oidc-jwks.json`) |
| Ожидаемый `sub` (кандидат) для `POLICY_REF=refs/heads/main` + `workflow_dispatch` | `repo:aiopslab/otus-diplom:ref:refs/heads/main:workflow_dispatch` — **КАНДИДАТ**, не подтверждённый SAN |
| Точный SAN (certificate identity) для `cosign --certificate-identity` | **ОТСУТСТВУЕТ** (владелец) — требует реального id-token подписанного запуска или явного значения владельца |
| audience id-token | **ОТСУТСТВУЕТ** (владелец) — discovery декларирует claim `aud`, значение не подтверждено |
| Trust-цепочка CA → issuer → audience → workflow binding + trust roots для sign/verify/verify-attestation | **ОТСУТСТВУЕТ** (владелец) |
| Офлайн-набор tooling (179 тестов) | **PASS** — `test_forgejo_lock_gate.py` (89) + `test_forgejo_offline_integration.py` (37) + `test_owner_gate_barrier.py` (48) + `test_cosign_cli_flags.py` (5); файл `offline-forgejo-suite.txt` |
| Синтаксис шаблона (после фиксации tools SHA) | **VERIFIED** — 4 job (`admission`/`test`/`preflight`/`release`), 93 выражения |
| `tools-pin-check --tools-dir .` против `46e77bc…` | **`tools_pin: true`** — все gate-режимы реализованы, обе CUE-политики совпали с ролями |

## Единый список нехватки данных (передано владельцу в #111)

| # | Отсутствующий факт | Ответственный | Требуемый ответ |
|---|---|---|---|
| 1 | Точное значение OIDC SAN — certificate identity (Forgejo id-token `sub`) для `cosign --certificate-identity`, привязка к одобренному workflow | Владелец (`gitaiopslab`) | Точное значение SAN + привязка к workflow (заменить `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>`) |
| 2 | audience id-token (значение `aud` в id-token Forgejo) | Владелец | Значение audience, сверяемое в `--certificate-oidc-issuer`/политике |
| 3 | Trust-цепочка: CA-доверие к issuer `https://git.aiopslab.online/api/actions`, audience, workflow binding, согласованные trust roots для sign/verify/verify-attestation | Владелец | Подтверждение trust-цепочки (CA → issuer → audience → binding) |

Дополнительно, НЕ входит в этот наряд (фиксируется для архитектора): плейсхолдер
`<FORGEJO_CHECKOUT_SHA>` (8 вхождений) остаётся в шаблоне; его значение известно из
`portal/tools/pins.lock.json` (`actions.checkout` → `11bd71901bbe5b1630ceea73d27597364c9af683`,
v4.2.2) — подстановка до публикации, отдельным решением.

## Границы соблюдены

Workflow НЕ публиковался и НЕ активировался; dispatch НЕ выполнялся; build/push/sign/attest
НЕ выполнялись; действующие pins/секреты/`images.lock`/`versions.lock`/`pins.lock.json`
НЕ менялись. Опубликованный workflow `main` (`.forgejo/workflows/…`, протухший tools pin
`32a38ea…`) для обхода review НЕ использовался и НЕ менялся. Секреты/токены в отчёт не
включены. Digest/provenance: `NOT_VERIFIED`.

```text
OWNER_SAN_CONFIRMATION        = MISSING (владелец)
OWNER_AUDIENCE_CONFIRMATION   = MISSING (владелец)
OWNER_TRUST_CHAIN_CONFIRMATION= MISSING (владелец)
TOOLS_SHA_FINALIZED           = YES (46e77bc9a31e43c333b73337bd928bc424e046b8)
WORKFLOW_BLOB_SHA             = 96237e87a3be7bba7e9fb74d802397b8119763ab (blob)
WORKFLOW_IDENTITY             = PLACEHOLDER (не подтверждена)
WORKFLOW_PUBLICATION / DISPATCH / BUILD / PUSH / SIGN / ATTEST = NOT_AUTHORIZED
LOCK_UPDATE                   = NOT_PERFORMED (apply_lock = false)
APPLICATION_DIGEST / SLSA_PROVENANCE = NOT_VERIFIED
```

## Критерии проверки (архитектор)

1. `PINNED_TOOLS_SHA` == `46e77bc9a31e43c333b73337bd928bc424e046b8`, `tools-pin-check`
   по нему даёт `tools_pin: true`; плейсхолдер `<FORGEJO_TOOLS_SHA>` отсутствует.
2. `WORKFLOW_IDENTITY` == `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` (не угадан); SAN/audience/
   trust-цепочка названы как отсутствующие с ответственным — владелец.
3. Blob неактивного шаблона `96237e87a3be7bba7e9fb74d802397b8119763ab` соответствует
   содержимому `portal/tools/p8c-portal-forgejo-release.yml.template` в ветке.
4. Никаких build/push/sign/attest/lock-update/publish/dispatch инженером не выполнялось.
5. Отчёт не содержит секретов/токенов; запрос владельцу передан в #111.
