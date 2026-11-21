# P8C #85 — Лист допуска этапа B (`apply_lock=false`)

Статус: `AUTHOR_PROPOSAL` (подготовлено инженером `hermes-5.187.1.37-engineer`).
**Вердикт допуска: BLOCKED** — входы для запуска этапа B подготовлены не полностью.

Основание:
- наряд #85: `docs/architecture/P8C_HANDOFF_84.md`, SHA `d2f9b39732c19dc8f98ce4e68325b5c6b68fbdcd`;
- решение владельца #73 (вариант B → C, реестр Forgejo `git.aiopslab.online`);
- offline-приёмка PR #78 (review #83): head `32a38ea1223ab8b0e10913a3c32c95d62c2661c6`, base `aeed3b314fa0fc00626310dec8a4a9f81d3f248b`.

`apply_lock` = `false` (этап B). Запись lock на этом этапе НЕ выполняется; digest и
provenance возвращаются владельцу для изучения перед отдельным решением о C.

```text
STAGE_B_ADMISSION              = BLOCKED
PINNED_SOURCE_SHA              = VERIFIED      (4c09d6b4a85e2d021516244988f48b92eade7acf)
PINNED_TOOLS_SHA               = NOT_FIXED     (<FORGEJO_TOOLS_SHA>; кандидат 32a38ea1223ab8b0e10913a3c32c95d62c2661c6)
WORKFLOW_SHA (policy pin)      = NOT_PROVIDED  (secret POLICY_WORKFLOW_SHA владельца, вне git)
REGISTRY                       = VERIFIED      (git.aiopslab.online, решение #73)
ACTIONS_SECRETS                = NOT_CONFIRMED (OWNER_GATE / POLICY_WORKFLOW_SHA / REGISTRY_USERNAME / REGISTRY_TOKEN)
APPLICATION_DIGEST / SLSA_PROVENANCE = NOT_VERIFIED (не существуют до фактической сборки)
WORKFLOW_PUBLICATION / DISPATCH / BUILD / PUSH / SIGN / ATTEST / LOCK_UPDATE = NOT_AUTHORIZED / NOT_PERFORMED
```

---

## 1. Неизменяемые SHA — сверка с кандидатом и подтверждением владельца

| SHA | Значение | Где закреплён (кандидат `32a38ea…`) | Подтверждение владельца | Статус |
|---|---|---|---|---|
| `PINNED_SOURCE_SHA` | `4c09d6b4a85e2d021516244988f48b92eade7acf` | `portal/tools/forgejo_lock_gate.py` L111; шаблон env L71 | решение #73 п.1: смена `portal/versions.lock:image.registry` на `git.aiopslab.online/aiopslab/otus-diplom-portal` → новый source SHA | **VERIFIED** |
| `PINNED_SOURCE_TREE_SHA256` | `e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01` | `forgejo_lock_gate.py`; шаблон env | решение #73 п.1 (обновить tree-hash) | **VERIFIED** (независимо пересчитан — совпал) |
| `PINNED_TOOLS_SHA` | `<FORGEJO_TOOLS_SHA>` (плейсхолдер) | `forgejo_lock_gate.py` L112; шаблон env L72 | — (фиксируется при публикации) | **NOT_FIXED** |
| workflow SHA (policy pin) | `secrets.POLICY_WORKFLOW_SHA` | вне git (repo secret) | владелец (вне git) | **NOT_PROVIDED** |

Ссылки: source `4c09d6b…` — https://git.aiopslab.online/aiopslab/otus-diplom/commit/4c09d6b4a85e2d021516244988f48b92eade7acf; кандидат `32a38ea…` — https://git.aiopslab.online/aiopslab/otus-diplom/commit/32a38ea1223ab8b0e10913a3c32c95d62c2661c6.

Сверка кандидата tools: коммит `32a38ea…` несёт все 5 tools-файлов
(`forgejo_lock_gate.py`, `test_forgejo_lock_gate.py`,
`test_forgejo_offline_integration.py`, `check_forgejo_workflow_syntax.py`,
`p8c-portal-forgejo-release.yml.template`) и корневой `images.lock` с записью
`otus-diplom-portal` (`image: git.aiopslab.online/aiopslab/otus-diplom-portal`,
`tag: candidate`, `digest: NOT_VERIFIED`, `verified: false`) — соответствует
требованию #76 («при публикации `PINNED_TOOLS_SHA` укажет на коммит, содержащий и
`forgejo_lock_gate.py`, и корневой `images.lock` с записью Portal, на/после
`aeed3b3…`»).

**SHA отчётов архитектора НЕ являются tools/workflow SHA.** Отчёт review #83
(`150222774a37a55849d18c0b60c2770a9fbd0e92`) и handoff #84
(`d2f9b39732c19dc8f98ce4e68325b5c6b68fbdcd`) — документальные коммиты; они не
закреплены как `PINNED_TOOLS_SHA` и не являются SHA активного workflow.

---

## 2. Целевой registry и P0-параметры (решение владельца #73)

| Параметр (пункт #73) | Значение | Где закреплён (шаблон `32a38ea…`) | Статус |
|---|---|---|---|
| `REGISTRY` (п.4) | `git.aiopslab.online` | env L95 | **VERIFIED** |
| `OWNER_IDENTITY` (п.5) | `gitaiopslab` | env L96 | **VERIFIED** |
| `IMAGE` (п.6) | `git.aiopslab.online/aiopslab/otus-diplom-portal` | env L97 | **VERIFIED** (байтово совпадает с `portal/versions.lock:image.registry`) |
| `SELF_HOSTED_RUNNER_LABEL` (п.7) | `otus-diplom` | `runs-on: otus-diplom` (3 jobs) | **VERIFIED** (регистрация runner — владелец, §4 п.7) |
| digest home (п.10) | корневой `images.lock`, запись `otus-diplom-portal` | `images.lock` (component `otus-diplom-portal`) | **VERIFIED** (запись есть, digest `NOT_VERIFIED`) |
| registry-путь (п.11) | self-hosted Forgejo | env L95 | **VERIFIED** |

`portal/versions.lock:image.registry` на source `4c09d6b…` =
`git.aiopslab.online/aiopslab/otus-diplom-portal` — совпадает с `IMAGE`
(проверка `lock-image-check` до push пройдёт по этому значению).

---

## 3. Статус подготовки Actions secrets (без значений)

| Secret | Назначение | Статус | Кто предоставляет |
|---|---|---|---|
| `OWNER_GATE` | допуск владельца (typed JSON) | **NOT_CONFIRMED** | владелец |
| `POLICY_WORKFLOW_SHA` | out-of-band policy pin workflow SHA | **NOT_CONFIRMED** | владелец |
| `REGISTRY_USERNAME` | логин registry | **NOT_CONFIRMED** | владелец |
| `REGISTRY_TOKEN` | пароль/токен registry | **NOT_CONFIRMED** | владелец |

Значения секретов в git не публикуются (правило «секреты вне git»). Статус
NOT_CONFIRMED: инженер не имеет доступа к чтению секретов; подтверждение
готовности — за владельцем.

---

## 4. Отсутствующие входы (блокеры) — кто предоставляет и куда передать подтверждение

| # | Вход | Кто предоставляет | Куда передать подтверждение |
|---|---|---|---|
| 1 | `PINNED_TOOLS_SHA` (плейсхолдер → SHA кандидата `32a38ea…`) | инженер фиксирует кандидат; **архитектор подтверждает при публикации** | в наряд на публикацию / ре-ревью |
| 2 | `secrets.POLICY_WORKFLOW_SHA` | **владелец** (вне git) | Forgejo: repo Settings → Actions → Secrets |
| 3 | `secrets.OWNER_GATE` | **владелец** (вне git) | Forgejo: repo Settings → Actions → Secrets |
| 4 | `secrets.REGISTRY_USERNAME` / `secrets.REGISTRY_TOKEN` | **владелец** (вне git) | Forgejo: repo Settings → Actions → Secrets |
| 5 | `actions/checkout@<FORGEJO_CHECKOUT_SHA>` (6 мест в шаблоне) | инженер закрепляет / **архитектор подтверждает** | при публикации |
| 6 | публикация workflow в `.forgejo/workflows/p8c-portal-forgejo-release.yml` | **архитектор** (решение) | отдельный наряд |
| 7 | регистрация self-hosted runner (label `otus-diplom`) | **владелец** | runner (вне git) |
| 8 | runtime-контекст `GITHUB_WORKFLOW_SHA` / `github.*` | **архитектор** — подтверждает при первом разрешённом запуске (fail-closed) | preflight первого запуска |

---

## 5. Вердикт

**BLOCKED.**

Подтверждено и готово:
- source SHA `4c09d6b…` + полнота дерева `e273368f…` (независимо пересчитан — совпал);
- целевой registry `git.aiopslab.online` и P0-параметры владельца (#73) уже
  закреплены в шаблоне (REGISTRY / OWNER_IDENTITY / IMAGE / runner label);
- digest home — корневой `images.lock` с записью `otus-diplom-portal` (digest `NOT_VERIFIED`);
- offline-приёмка PR #78 (review #83) — повторное ревью lock-правки не требуется.

Отсутствуют (блокируют запуск B):
- фиксация `PINNED_TOOLS_SHA` (плейсхолдер `<FORGEJO_TOOLS_SHA>`);
- `POLICY_WORKFLOW_SHA` и registry-секреты (`OWNER_GATE`, `REGISTRY_USERNAME`,
  `REGISTRY_TOKEN`) — владелец, вне git;
- `FORGEJO_CHECKOUT_SHA`, публикация workflow, регистрация runner.

Следующее требуемое подтверждение:
- **владелец** — подготовка Actions secrets (§3; §4 пп. 2–4, 7);
- **архитектор** — решение о публикации workflow и фиксация `PINNED_TOOLS_SHA` /
  `FORGEJO_CHECKOUT_SHA` (§4 пп. 1, 5–6).

После закрытия этих входов — отдельное решение владельца о запуске B
(`apply_lock=false`): один запуск (test/preflight/release: build/push/sign/attest),
digest+provenance возвращаются владельцу, lock НЕ записывается. C
(`apply_lock=true`) — только по отдельному подтверждению точной пары после
изучения digest+provenance.

В рамках наряда workflow не активировался, образ не публиковался, `images.lock`
не менялся, C не запускался.

```text
VERDICT = BLOCKED
```
