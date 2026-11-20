# P8C #66 — Лист решения владельца: первый запуск Forgejo Actions

Статус: `AUTHOR_PROPOSAL` (подготовлено инженером; решение — за владельцем).
Основание: архитектор issue #66 → решение в коммите
`2a04ee27e516a8d7d5871a9632fdba0b10f418a1` (`docs/architecture/P8C_HANDOFF_66.md`).
Offline-приёмка шаблона: PR #65 (`f76f59b03e3ca85ab2ae275522e5c02498ce2a64`) на head
`4f691ea675c6a0e0dc769ad3847dd4e705c4dc93` (PR #51, ветка `engineer/49-forgejo-build-spec`).
Шаблон ПРИНЯТ offline; повторное исправление не требуется. **Выпуск НЕ разрешён** —
offline-приёмка не подтверждает digest/provenance.

**`apply_lock` по умолчанию = `false`.** Любая запись lock требует явной авторизации
владельца (`inputs.apply_lock == true`).

---

## 1. Известные SHA (закреплены, со ссылками)

| Роль | Значение | Ссылка |
|---|---|---|
| Source pin (неизменный) — исходники приложения + `Containerfile` + `install-verified-go.sh` | `d22aa8f1170deaf09580518916ea02c7c4d8bfba` | https://git.aiopslab.online/aiopslab/otus-diplom/commit/d22aa8f1170deaf09580518916ea02c7c4d8bfba |
| Полнота дерева source — sha256 отсортированного **перечня путей** (`git ls-tree -r --name-only`), контроль путей, не содержимого | `e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01` | [шаблон `PINNED_SOURCE_TREE_SHA256` (L73)](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/4f691ea675c6a0e0dc769ad3847dd4e705c4dc93/portal/tools/p8c-portal-forgejo-release.yml.template#L73) |
| Head шаблона/workflow (PR #51, принят offline) | `4f691ea675c6a0e0dc769ad3847dd4e705c4dc93` | https://git.aiopslab.online/aiopslab/otus-diplom/commit/4f691ea675c6a0e0dc769ad3847dd4e705c4dc93 |
| Заключение offline-приёмки (PR #65) | `f76f59b03e3ca85ab2ae275522e5c02498ce2a64` | https://git.aiopslab.online/aiopslab/otus-diplom/commit/f76f59b03e3ca85ab2ae275522e5c02498ce2a64 |
| Решение архитектора (этот наряд #66/#67) | `2a04ee27e516a8d7d5871a9632fdba0b10f418a1` | https://git.aiopslab.online/aiopslab/otus-diplom/commit/2a04ee27e516a8d7d5871a9632fdba0b10f418a1 |

> Контрольный хеш дерева source — это sha256 **перечня путей**, не содержимого:
> `git ls-tree -r --name-only d22aa8f1170deaf09580518916ea02c7c4d8bfba | LC_ALL=C sort | sha256sum`
> = `e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01`. Без `--name-only`
> результат иной (хешировались бы полные записи `ls-tree` — mode/type/blob-SHA, а не только пути).

Закреплённые toolchain-версии (уже в шаблоне / `portal/versions.lock` / `pins.lock.json`):
Go `1.27.3` (`65efbc80…`), BuildKit `v0.34.0`, rootlesskit `v2.3.1`, syft `v1.55.0`,
trivy `v0.76.0`, cosign `v3.1.3`. GitHub action-форки (SHA не переносятся на Forgejo):
`actions/checkout` `11bd71901bbe5b1630ceea73d27597364c9af683`,
`docker/login-action` `9780b0c442fbb1117ed29e0efdff1e18412f7567`,
`actions/upload-artifact` `65462800fd760344b1a7b4382951275a0abb4808`.

**Tools SHA НЕ известен** — `PINNED_TOOLS_SHA = <FORGEJO_TOOLS_SHA>` (плейсхолдер),
см. §2 п.1. OIDC-параметры (шаблон `4f691ea`, строки 94–97):
- **Обнаруженный issuer** (подтверждён read-only discovery): `https://git.aiopslab.online` —
  это `OIDC_ISSUER`.
- **Ожидаемая certificate identity** (`WORKFLOW_IDENTITY`, **ещё НЕ проверена** — до первого
  реального подписанного запуска):
  `https://git.aiopslab.online/aiopslab/otus-diplom/.forgejo/workflows/p8c-portal-forgejo-release.yml@refs/heads/main`.
  Discovery доказывает существование issuer, но **не** identity будущей подписи — её подтвердит
  только `cosign verify --certificate-identity` / `--certificate-oidc-issuer` на первом
  подписанном запуске.

---

## 2. Неизвестные параметры публикации (NOT_VERIFIED) — кто подтверждает, до какого действия

| # | Параметр (плейсхолдер в шаблоне) | Кто подтверждает | До какого действия |
|---|---|---|---|
| 1 | `PINNED_TOOLS_SHA` (`<FORGEJO_TOOLS_SHA>`) — SHA коммита, несущего Forgejo-инструментарий | Архитектор (фиксирует при публикации; не существует до слияния) | checkout tools-дерева / любой первый запуск |
| 2 | `secrets.POLICY_WORKFLOW_SHA` — out-of-band policy pin workflow SHA | Владелец (repo secret вне git) | preflight owner-gate (тройная сверка, fail-closed) |
| 3 | `secrets.OWNER_GATE` — допуск владельца (typed JSON secret) | Владелец | preflight owner-gate |
| 4 | `REGISTRY` (`<REGISTRY_HOST_OWNER_SUPPLIED>`) — доверенный registry host | Владелец (P0) | registry manifest fetch / login |
| 5 | `OWNER_IDENTITY` (`<OWNER_IDENTITY_P0>`) | Владелец | owner-gate (сверка с `github.actor`) |
| 6 | `IMAGE` (`<FULL_IMAGE_REF_OWNER_SUPPLIED>`) — полный ref, обязан байтово совпадать с `portal/versions.lock:image.registry` | Владелец | `lock-image-check` до push |
| 7 | `<SELF_HOSTED_RUNNER_LABEL>` — метка self-hosted runner | Владелец (регистрация runner) | назначение jobs |
| 8 | `secrets.REGISTRY_USERNAME` / `secrets.REGISTRY_TOKEN` | Владелец | `docker login` (только после preflight) |
| 9 | `<FORGEJO_CHECKOUT_SHA>` — SHA Forgejo-форка `actions/checkout` | Инженер закрепляет / Архитектор подтверждает | checkout steps |
| 10 | Домашнее место digest: `images.lock` (нет записи `portal`) vs `portal/versions.lock:image.digest` | Владелец / Архитектор (решение GAP §1.5.1) | запись lock (`apply_lock=true`) |
| 11 | Registry-путь: `ghcr.io/dedvmedved-dot/otus-diplom-portal` vs Forgejo/self-hosted доверенный канал | Владелец (P0) | push |
| 12 | Публикация workflow в `.forgejo/workflows/` + gate-документ / бюджет dispatch | Архитектор (решение) | любой запуск |
| 13 | `GITHUB_WORKFLOW_SHA` / `github.*` (runtime-контекст) на self-hosted Forgejo runner | Архитектор — подтверждает наблюдаемый runtime-контекст (`github.actor` / `github.repository` / `github.ref` / `GITHUB_WORKFLOW_SHA`) при первом разрешённом запуске (gate fail-closed) | preflight / verify; **без успешной проверки переход к release запрещён** |
| 14 | Независимая ревизия CA/UID + подтверждение pull владельцем OTUS | Владелец OTUS | открытие окна |

---

## 3. Варианты решения владельца (отказ / допуск к конкретному запуску)

- **A. ОТКАЗ** — workflow не публикуется, запуск не выполняется. Digest/provenance
  остаются `NOT_VERIFIED`; lock не меняется.
- **B. ДОПУСК к конкретному запуску, `apply_lock=false` (ПО УМОЛЧАНИЮ)** — публикация
  workflow + один запуск (`test`/`preflight`/`release`: build/push/sign/attest);
  digest+provenance фиксируются в evidence-памяти, но lock **НЕ** записывается
  (`image.digest` остаётся `NOT_VERIFIED`).
- **C. ДОПУСК с `apply_lock=true`** — то же, что B, плюс явная авторизация записи
  пары (полный image, digest) в `portal/versions.lock:image` после прохождения gate.

Владелец может допустить конкретный запуск (B) отдельно от записи lock (C) —
например, сначала один проверочный запуск B, затем решение о C после изучения
полученного digest+provenance.

---

## 4. Следующее требуемое подтверждение

Требуется **РЕШЕНИЕ ВЛАДЕЛЬЦА** (это следующий блокирующий шаг):

1. выбор варианта **A / B / C** (§3);
2. при B или C — передача P0-параметров **вне git** (§2 пп. 2–8, 11) и решение п.10.

До этого решения: workflow **не активируется**, секреты **не запрашиваются**,
build/push/sign/attest **не выполняются**, lock **не меняется**.

```text
OWNER DECISION = REQUIRED (A / B / C + P0-параметры вне git)
WORKFLOW_PUBLICATION / DISPATCH / BUILD / PUSH / SIGN / ATTEST = NOT_AUTHORIZED
LOCK_UPDATE = NOT_PERFORMED (apply_lock = false)
APPLICATION_DIGEST / SLSA_PROVENANCE = NOT_VERIFIED
```
