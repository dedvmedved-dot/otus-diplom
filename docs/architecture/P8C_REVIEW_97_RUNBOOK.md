# P8C #97 — перепубликация workflow и перепиновка (repin) после review #95

Роль: Implementation Engineer (Hermes). Источник: issue #97, решение архитектора
[P8C_REVIEW_95.md](P8C_REVIEW_95.md) (commit `420ecc3822092b195d1d02271f16adb1b650ebc4`).

Этот документ — **инструкция**, а не разрешение на запуск. Он описывает, что сделано в PR
и какие шаги владелец выполняет ПОСЛЕ повторного review архитектора. Настоящее ревью не
разрешает dispatch, выпуск, смену секретов или lock, и **первый B остаётся BLOCKED**.

## 1. Что сделано в PR (ветка `engineer/97-owner-gate-race-oidc`)

### 1/A1 — наблюдение workflow-blob (принято, внесено во все потребители)

`GITHUB_WORKFLOW_SHA` в Forgejo 15.0.11 **не существует** (ни blob, ни commit — переменной
нет, runner оставляет её unset). Вместо неё:

- В `preflight` и `release` добавлен **третий checkout** репозитория на точном
  dispatch-коммите (`${{ github.sha }}`, `path: workflow`), отдельно от `src`/`tools`.
- Новый шаг «Observe executed workflow blob» вычисляет
  `git rev-parse <github.sha>:.forgejo/workflows/p8c-portal-forgejo-release.yml` через новую
  команду `forgejo_lock_gate.py workflow-blob` и проверяет, что объект — **`blob`**
  (`git cat-file -t`). Отсутствие пути, не-blob или неверный commit — отказ до побочных эффектов.
- Вычисленный blob (`OBSERVED_WORKFLOW_SHA`) подставляется во ВСЕ потребители:
  triple-check preflight (`--observed-workflow-sha`), `predicate` (workflow SHA),
  evidence bundle (`workflow_sha` + `observed_workflow_sha`), final gate.
- Ни `workflow_ref`, ни значение из самого секрета не используются как наблюдение.

### 0 — эксклюзивный барьер до PickTask (BLOCKED до подтверждения владельца)

- Добавлен job `admission` (`runs-on: otus-diplom-admission` — выделенный owner-controlled
  label), `needs` остальных job идут через него (`test.needs = admission`).
- Job fail-closed: требует `inputs.admission_confirmed == true`.
- Протокол владельца (из решения #95): **до** dispatch закрыть выдачу для label и подтвердить
  отсутствие активных/конкурирующих release runs; после 201 — gate для возвращённого
  id/attempt=1; PUT; после подтверждённого 201/204 — открыть выдачу. Не заменять/удалять gate
  до завершения release. При неподтверждённости — не открывать выдачу, отменить run, не rerun.
- **Статус: BLOCKED.** Эксклюзивный контроль label/runner на этом инстансе пока не подтверждён.

### 2/B — OIDC release-only (BLOCKED до подтверждения доверия)

- `enable-openid-connect: true` только на job `release` (именно он выдаёт id-token;
  `permissions.id-token: write` сам по себе credentials не выдаёт).
- Issuer исправлен на source-подтверждённый `https://git.aiopslab.online/api/actions`
  (`routers/api/actions/id_token.go` + discovery `/api/actions/.well-known/openid-configuration`),
  и в `forgejo_lock_gate.py` (`FORGEJO_OIDC_ISSUER`), и в env workflow.
- `WORKFLOW_IDENTITY` — явный плейсхолдер `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>`: `sub`
  dispatch (`repo:…:ref:…`) не доказывает SAN сертификата; значение **не угадывается**.
- Keyless sign/verify/verify-attestation загорожены `inputs.oidc_trust_confirmed` (default false,
  fail-closed до build/push/sign) и флагом gate `--oidc-trust-confirmed` (default BLOCKED в
  `decide_lock_update`).
- **Статус: BLOCKED.** Требуются: подтверждение доверия CA к issuer и audience, точный SAN,
  привязка к одобренному workflow, согласованные trust roots для sign/verify/verify-attestation.

### 3 — cosign URL и обе аттестации

- `COSIGN_VERSION: "v3.1.3"` → `"3.1.3"` (URL `…/download/v${COSIGN_VERSION}/…` давал `vv3.1.3`).
  SHA-256 проверка сохранена.
- Проверяются **обе** аттестации для того же digest (`cosign verify-attestation --type slsaprovenance`
  И `--type spdxjson`), с identity/issuer и аннотацией `-a ref=<PINNED_SOURCE_SHA>`.

## 2. Автономные тесты

Новый файл `portal/tools/test_owner_gate_barrier.py` (офлайн, синтетика, без CI/registry/secrets):
неверный blob (absent/non-blob/invalid commit/mismatch), задержка PUT (expired/future), чужой run,
неверный issuer/identity, OIDC trust не подтверждён, барьер/OIDC структура шаблона.
Плюс обновлён `test_forgejo_offline_integration.py` (baseline с `oidc_trust_confirmed`,
структурная проверка `--observed-workflow-sha "$OBSERVED_WORKFLOW_SHA"`).

## 3. Перепубликация и repin (владелец, ПОСЛЕ повторного review)

1. Архитектор принимает PR (повторное review изменённого workflow и gate).
2. **Публикация**: изменённый workflow фиксируется в `.forgejo/workflows/p8c-portal-forgejo-release.yml`
   в дереве `main`; фиксируется **merge commit** и **новый blob** `git rev-parse
   <merge_commit>:.forgejo/workflows/p8c-portal-forgejo-release.yml` (объект — `blob`).
3. **Repin POLICY_WORKFLOW_SHA** → новый blob (секрет репозитория). OWNER_GATE также должен
   нести `workflow_sha` = новый blob.
4. **Repin PINNED_TOOLS_SHA** → commit, где лежит изменённый `forgejo_lock_gate.py` + тесты +
   template (если tools менялись — да, добавился `workflow-blob` и OIDC-гейт).
5. **Подтвердить барьер**: выделенный runner/label `otus-diplom-admission` без других подходящих
   runners на всех уровнях; процедура закрытия/открытия выдачи из раздела 1.
6. **Подтвердить OIDC**: доверие CA к issuer (`https://git.aiopslab.online/api/actions`) и audience,
   точный SAN, привязка `sub` к одобренному workflow, согласованные trust roots; заменить
   `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` подтверждённым значением.
7. Только после п. 5–6 — **отдельное** решение о первом B. Это ревью не разрешает dispatch,
   выпуск, смену секретов или lock.

## 4. Замечания для ревьюера (не блокеры, вне объёма #97)

- Тот же паттерн `v${VERSION}` (двойная `v`) присутствует в URL загрузки **syft** и **trivy**
  (`syft_${SYFT_VERSION}_…`, `trivy_${TRIVY_VERSION}_…` при `SYFT_VERSION="v1.55.0"`,
  `TRIVY_VERSION="v0.76.0"`), а также `rootlesskit` (`v${ROOTLESSKIT_VERSION}`). Review #95
  назвал только cosign; для syft/trivy дополнительно нужно выверить имя ассета (в имени
  версия без `v`). Оставлено как есть, требует решения владельца/архитектора.
- SHA-256 для cosign `v3.1.3` не перепроверялся по сети (offline); значение сохранено, но
  перед публикацией его следует сверить с официальным `SHA256SUMS` релиза.
