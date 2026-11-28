# P8C #156 — сверка release identity / trust / admission (без запуска выпуска)

Роль: Implementation Engineer (Hermes). Наряд — [issue #156](https://git.aiopslab.online/aiopslab/otus-diplom/issues/156),
основание — [#155](https://git.aiopslab.online/aiopslab/otus-diplom/issues/155) и
[выписка владельца #153 comment 12397](https://git.aiopslab.online/aiopslab/otus-diplom/issues/153#issuecomment-12397).
Ветка — `engineer/156-verify-identity-trust-admission` (база `main`).

## Статус

`ANALYSIS_ONLY — NOT_READY_FOR_DISPATCH`. Сверка выполнена по уже закреплённым SHA
(`4c09d6b…` source, `46e77bc…` tools, `96237e87…` release-шаблон, `c2194b16…`
диагностика) и по фактическим OIDC claims из run 72. Никаких dispatch/rerun,
запроса токена, merge #140, изменения trust/policy, build/push/sign/attest/lock,
публикации. Итог: **пакет доказательств + BLOCKED** — остаются ровно три
подтверждения владельца (см. «Итог»).

## Источники и закреплённые SHA (использованы в этой сверке)

| Вещь | SHA / permalink |
|---|---|
| Закреплённый source tree | `4c09d6b4a85e2d021516244988f48b92eade7acf` |
| Закреплённый tools tree (после #118) | `46e77bc9a31e43c333b73337bd928bc424e046b8` |
| Release-шаблон (неактивный, после #118) — blob | `96237e87a3be7bba7e9fb74d802397b8119763ab` (`portal/tools/p8c-portal-forgejo-release.yml.template`) |
| Диагностический ref (run 72) | `c2194b161fe7e5e5218bd737c335faa63c41db0d` (`refs/heads/engineer/139-oidc-enable-openid`) |
| Run 70/71 (до апгрейда runner) | `95f6cb271b2da4053b157c81317c46641ac556d0` |
| Источник Forgejo сервер | v15.0.11 (`15.0.11+gitea-1.22.0`), локально сверено в `/root/forgejo-src` @ `v15.0.11` |
| Run 72 (OIDC claims) | https://git.aiopslab.online/aiopslab/otus-diplom/actions/runs/4 |
| Выписка владельца | [#153#issuecomment-12397](https://git.aiopslab.online/aiopslab/otus-diplom/issues/153#issuecomment-12397) |

## Таблица: требование / фактическое доказательство (permalink + SHA) / пробел

| # | Требование | Фактическое доказательство | Пробел |
|---|---|---|---|
| 1 | Точный OIDC issuer для `cosign --certificate-oidc-issuer` | **Подтверждено** — `https://git.aiopslab.online/api/actions`. Источники: (а) run 72 `OIDC_ISS=…/api/actions` ([#153#issuecomment-12397](https://git.aiopslab.online/aiopslab/otus-diplom/issues/153#issuecomment-12397)); (б) live discovery `GET /api/actions/.well-known/openid-configuration`; (в) source `routers/api/actions/id_token.go:142` (`claims["iss"] = TrimSuffix(AppURL,"/") + "/api/actions"`); (г) шаблон `OIDC_ISSUER` и гейт `FORGEJO_OIDC_ISSUER` уже закрепляют это значение | **НЕТ** (issuer закрыт) |
| 2 | Способ получения OIDC (Forgejo-native, не GitHub `permissions:`) | **Подтверждено** — run 72: `ENV_PRESENT ACTIONS_ID_TOKEN_REQUEST_URL` + `ENV_PRESENT ACTIONS_ID_TOKEN_REQUEST_TOKEN`, `OIDC_REQUEST_HTTP_STATUS=200` (инъекция runner v12.10.2). Ключ — `enable-openid-connect: true` (диагностический workflow @ `c2194b16…`; release-шаблон @ `96237e87…` на release-job). GitHub `permissions: id-token: write` Forgejo НЕ реализует ([#139](https://git.aiopslab.online/aiopslab/otus-diplom/issues/139), source `services/actions/task.go:162-186`) | **НЕТ** (механизм подтверждён) |
| 3 | audience id-token | **Подтверждено значение** — run 72 `OIDC_AUD=sigstore` (диагностика запрашивала `audience=sigstore`); source `routers/api/actions/id_token.go:111-119` (aud = query-param `audience`, дефолт `AppURL+repoOwner`). Ключевой signer (cosign/Sigstore) ожидает audience `sigstore` | **Частично** — «принятие» audience доверенным signer входит в trust-цепочку (строка 5) |
| 4 | Точный SAN / certificate identity для release | **Формат OIDC `sub` подтверждён**, значение `sub` для `main` — расчётное. Source `services/actions/auth.go:148-153` (`generateOIDCSub`): не-PR → `repo:{repository}:ref:{ref}` (строки 151/153). Run 72 `OIDC_SUB=repo:aiopslab/otus-diplom:ref:refs/heads/engineer/139-oidc-enable-openid` подтверждает формат на факте. **Ожидаемый `sub` для release (`refs/heads/main`), не SAN** = `repo:aiopslab/otus-diplom:ref:refs/heads/main` | **ПРОБЕЛ** — нет свидетельства о SAN, который выбранная CA выдаёт для release; даже наблюдение `sub` на `main` не закрыло бы пробел. `WORKFLOW_IDENTITY` остаётся плейсхолдером `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` |
| 5 | Trust-цепочка: CA-доверие к issuer+audience, workflow binding, trust roots для sign/verify/verify-attestation | Механизм закреплён: гейт `forgejo_lock_gate.py` — `OIDC_TRUST_CONFIRMED = False` (fail-closed), `identity_is_confirmed()` отклоняет плейсхолдер; release-job имеет fail-closed шаг `Verify OIDC trust + identity confirmation` по `inputs.oidc_trust_confirmed` | **ПРОБЕЛ** — `oidc_trust_confirmed` = false; владелец не подтвердил, какой signer (публичный sigstore Fulcio/Rekor или приватный) принимает Forgejo issuer `https://git.aiopslab.online/api/actions`, и какие trust roots используются |
| 6 | Verifier rule (правило проверки подписи/аттестации) | Зафиксировано: `cosign verify --certificate-identity $WORKFLOW_IDENTITY --certificate-oidc-issuer $OIDC_ISSUER -a ref=$PINNED_SOURCE_SHA`; `cosign verify-attestation --type slsaprovenance/spdxjson --policy cosign-slsa-policy.cue / cosign-spdx-policy.cue` (source-binding по `4c09d6b…`, SPDX-shape). Все три файла закреплены в tools `46e77bc…` | **Частично** — `--certificate-identity` ссылается на плейсхолдер SAN (строка 4) |
| 7 | Эксклюзивный admission-барьер (runner/label, закрытие выдачи, нет конкурирующих runs, gate PUT 201/204) | Механизм закреплён: release-шаблон имеет job `admission` на `runs-on: otus-diplom-admission`, fail-closed по `inputs.admission_confirmed` («barrier before PickTask»). Runner `otus-diplom` несёт label `otus-diplom-admission` ([#148#issuecomment-12351](https://git.aiopslab.online/aiopslab/otus-diplom/issues/148#issuecomment-12351)) | **ПРОБЕЛ** — `admission_confirmed` = false; закрытие выдачи по label + подтверждение отсутствия конкурирующих release-runs + gate PUT (201/204) на возвращённый run id — действие владельца, не выполнено |
| 8 | Release workflow/ref зафиксирован и опубликован | `POLICY_REF = refs/heads/main`, workflow name `p8c-portal-forgejo-release`, путь `.forgejo/workflows/p8c-portal-forgejo-release.yml`. Неактивный шаблон `96237e87…` (в `portal/tools/`, Forgejo его не запускает) | **ПРОБЕЛ** — активный workflow в `main` ПРОТУХШИЙ: `PINNED_TOOLS_SHA=32a38ea…`, `OIDC_ISSUER=https://git.aiopslab.online` (без `/api/actions`), `WORKFLOW_IDENTITY` в GitHub-формате (`…@refs/heads/main`), `permissions: id-token: write` без `enable-openid-connect`. Публикация финального шаблона не выполнялась (нужно отдельное решение архитектора/владельца) |

## Проверка архитектора #159

[PR #158 на проверенном SHA](https://git.aiopslab.online/aiopslab/otus-diplom/commit/dc268ebcf295d863c0b25510596e2c1b6f281951) меняет только этот отчёт. Пакет принят как анализ; выпуск B — BLOCKED / NOT_READY_FOR_DISPATCH.

- Строки 1–4: [выписка по run 72, task 225](https://git.aiopslab.online/aiopslab/otus-diplom/issues/153#issuecomment-12397) и [generateOIDCSub, v15.0.11](https://codeberg.org/forgejo/forgejo/src/tag/v15.0.11/services/actions/auth.go#L148-L155). Для `workflow_dispatch` действует ветвь `default`, не `pull_request`. Выписка доказывает `sub` диагностического запуска, но не SAN сертификата.
- Строки 5–7: [гейт](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/46e77bc9a31e43c333b73337bd928bc424e046b8/portal/tools/forgejo_lock_gate.py) и [исходный шаблон в tools](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/46e77bc9a31e43c333b73337bd928bc424e046b8/portal/tools/p8c-portal-forgejo-release.yml.template). Его blob `4fc1768d5ec6cf9b64ff7aa55c1b685eb59a51c3` и закреплённый blob `96237e87a3be7bba7e9fb74d802397b8119763ab` сверены: единственная разница — подстановка `PINNED_TOOLS_SHA`. Admission предшествует остальным jobs по цепочке `needs`, не обязательно напрямую.
- Строка 8: [активный workflow на проверенной базе main](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/53dcd7fc91e53979df687f43578bd75e0ff9c9cc/.forgejo/workflows/p8c-portal-forgejo-release.yml) не эквивалентен закреплённому шаблону. Подтверждения владельца не разрешают автоматически ни публикацию, ни dispatch.

## Отдельные сверки

### A. Release workflow/ref и способ получения OIDC

- **Ref**: `refs/heads/main` (`POLICY_REF` в шаблоне и гейте). Диагностический ref
  `refs/heads/engineer/139-oidc-enable-openid` — НЕ release ref.
- **Способ получения OIDC**: `enable-openid-connect: true` на release-job (шаблон
  `96237e87…`). Подтверждён фактом run 72 (env-инъекция + HTTP 200). GitHub-стиль
  `permissions:` в Forgejo неэффективен (#139; `services/actions/task.go:162-186`).
- **Ключевая дивергенция**: опубликованный workflow в `main` всё ещё использует
  `permissions:` и НЕ имеет `enable-openid-connect`; финальный шаблон с корректным
  ключом — неактивный (`portal/tools/`). До публикации финального шаблона release
  workflow как таковой не готов (строка 8 таблицы).

### B. Принятие issuer/audience доверенным signer

- **issuer**: `https://git.aiopslab.online/api/actions` (подтверждено, строка 1).
- **audience**: `sigstore` (подтверждено значение, строка 3).
- **Принятие signer'ом**: НЕ подтверждено. Keyless-подпись идёт через Fulcio
  (cert) + Rekor (transparency). Публичный sigstore Fulcio принимает ограниченный
  список OIDC-issuer'ов; доверие к Forgejo-issuer'у
  `https://git.aiopslab.online/api/actions` и согласованные trust roots
  (Fulcio root CA, Rekor log, TUF) владельцем не подтверждены. В release-шаблоне
  это fail-closed `inputs.oidc_trust_confirmed` (default `false`) + `OIDC_TRUST_CONFIRMED=False`
  в гейте.

### C. Фактический сертификатный SAN и правило verifier

- **OIDC `sub` наблюдался; сертификат и его SAN не наблюдались.** Соответствие `sub` → SAN зависит от выбранной CA и её правила выдачи. Для `cosign --certificate-identity` нужно подтверждение точного SAN, а не только формата `sub`.
  Формат `repo:{owner}/{repo}:ref:{ref}` подтверждён source (`services/actions/auth.go:148-153`)
  и фактом run 72 (`sub=repo:aiopslab/otus-diplom:ref:refs/heads/engineer/139-oidc-enable-openid`).
  Ожидаемый OIDC `sub` для release (не SAN) = `repo:aiopslab/otus-diplom:ref:refs/heads/main`.
- **Правило verifier**: `cosign verify --certificate-identity <SAN> --certificate-oidc-issuer <issuer>`
  (+ `-a ref=<source>` для image-подписи); `verify-attestation` с CUE-политиками
  `cosign-slsa-policy.cue` / `cosign-spdx-policy.cue`; финальный гейт
  `forgejo_lock_gate.py verify … --identity --issuer --oidc-trust-confirmed`.
  Сейчас `--certificate-identity`/`WORKFLOW_IDENTITY` = плейсхолдер
  `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` → любой keyless-verify был бы отклонён.
- **Коррекция кандидата из #118**: предыдущий кандидат
  `repo:aiopslab/otus-diplom:ref:refs/heads/main:workflow_dispatch` (с суффиксом
  события) **опровергнут** фактом run 72 — фактический sub суффикса события НЕ
  несёт (`…:ref:refs/heads/engineer/139-oidc-enable-openid`). Верный формат —
  `repo:{repository}:ref:{ref}` без `:workflow_dispatch`.

### D. Admission-барьер

- Механизм зафиксирован (шаблон `96237e87…`): job `admission` на выделенном
  owner-контролируемом label `otus-diplom-admission`, зависимость от `admission` по цепочке `needs` у всех
  последующих jobs, fail-closed `inputs.admission_confirmed` («STOP: exclusive
  admission barrier not confirmed by owner (BLOCKED)»).
- Label существует на runner (`otus-diplom-admission` в списке labels,
  [#148#issuecomment-12351](https://git.aiopslab.online/aiopslab/otus-diplom/issues/148#issuecomment-12351)).
- Не выполнено (владелец): закрытие выдачи по label до dispatch; подтверждение
  отсутствия активных/конкурирующих release-runs; формирование gate (возвращённый
  run id / attempt=1) и подтверждённый PUT 201/204 до повторного открытия выдачи.

## Диагностический sub НЕ переносится в release policy

Соблюдено: наблюдаемый sub диагностической ветки
`repo:aiopslab/otus-diplom:ref:refs/heads/engineer/139-oidc-enable-openid`
использован ТОЛЬКО как доказательство формата. В release policy
(`WORKFLOW_IDENTITY`, гейт, шаблон) значение НЕ внесено — оно остаётся
плейсхолдером. Ожидаемый `sub` для `main` не задаёт certificate identity. Никаких записей в
trust/policy/шаблон инженером не делалось.

## Итог (для архитектора и владельца)

Пакет доказательств собран: issuer, audience, формат sub, способ получения OIDC,
правило verifier и механизм admission-барьера — все зафиксированы с permalink и
SHA. Выпуск B остаётся `NOT_READY_FOR_DISPATCH`; остаются ровно ТРИ подтверждения
владельца (ни одно не выполнимо инженером без выхода за границы наряда):

1. **Точный SAN** — владелец указывает точную certificate identity для `cosign --certificate-identity` и основание: SAN ранее выданного сертификата соответствующего release-контекста либо однозначное правило выдачи выбранной CA для этого workflow/ref. Формат `sub` не заменяет это свидетельство.

2. **Trust-цепочка** — подтвердить signer/CA (публичный sigstore Fulcio/Rekor или
   приватный) и trust roots для sign/verify/verify-attestation, принимающие
   Forgejo issuer `https://git.aiopslab.online/api/actions` + audience `sigstore`.
   Минимальный запрос: «подтверди oidc_trust_confirmed: CA/trust roots».

3. **Admission-барьер** — до dispatch закрыть выдачу по label
   `otus-diplom-admission`, подтвердить отсутствие конкурирующих release-runs,
   сформировать gate на возвращённый run id и подтвердить PUT 201/204.
   Минимальный запрос: «подтверди admission_confirmed: барьер установлен до
   dispatch».

После этих трёх подтверждений: подстановка SAN в шаблон/гейт, публикация
финального шаблона в `.forgejo/workflows/` (заменяет протухший активный workflow)
и повторный review — всё отдельными решениями архитектора/владельца. Внесение
диагностического sub в release policy исключено.

## Границы соблюдены

dispatch/rerun не выполнялись; запрос id-token/jwt не выполнялся; merge #140 не
выполнялся; trust/policy/шаблон/гейт/workflow не изменялись;
build/push/sign/attest/lock/публикация не выполнялись; активный workflow `main` не
трогался. Секреты/токены/JWT/значения env в отчёт не включены. Digest/provenance:
`NOT_VERIFIED`.

```text
OIDC_ISSUER                   = CONFIRMED (https://git.aiopslab.online/api/actions)
OIDC_AUDIENCE                 = CONFIRMED_VALUE (sigstore)
OIDC_SUB_FORMAT               = CONFIRMED (repo:{repository}:ref:{ref}, no event suffix)
RELEASE_SAN (refs/heads/main) = UNKNOWN (certificate not observed; CA mapping not confirmed)
WORKFLOW_IDENTITY (policy)    = PLACEHOLDER (not touched)
OIDC_TRUST_CHAIN              = MISSING (owner)
EXACT_SAN_CONFIRMATION        = MISSING (owner)
ADMISSION_BARRIER             = MISSING (owner, admission_confirmed=false)
RELEASE_WORKFLOW_PUBLISHED    = NO (main workflow is stale 32a38ea…)
DISPATCH / BUILD / PUSH / SIGN / ATTEST / LOCK / PUBLISH = NOT_PERFORMED
DIGEST / PROVENANCE           = NOT_VERIFIED
```

## Критерии проверки (архитектор)

1. Каждый факт в таблице несёт permalink и/или SHA; ни один факт не выведен «из
   памяти» (issuer/aud/sub — из run 72 + source v15.0.11, верифицировано локально).
2. Формат sub `repo:{repository}:ref:{ref}` (без суффикса события) подтверждён
   source (`auth.go:148-153`) И фактом run 72; кандидат #118 `…:workflow_dispatch`
   помечен опровергнутым.
3. Диагностический sub НЕ внесён в release policy (`WORKFLOW_IDENTITY` остался
   плейсхолдером; изменений trust/policy/шаблона нет).
4. BLOCKED содержит три точных недостающих свидетельства с исполнителем
   (владелец) и минимальным запросом допуска; выпуск B — NOT_READY_FOR_DISPATCH.
5. Отчёт не содержит секретов/токенов/JWT/значений env.
