# P8C §6 — наряд #42: ответ инженера (запрос входных свидетельств у владельцев)

Роль: Implementation Engineer, assignee `hermes-5.187.1.37-engineer`.
Основание: наряд `docs/architecture/P8C_RUNTIME_GATE_42.md` @ `2d37643dff3c83c8eea3f096d322397ffaa4c050`.
Принятый source: `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (Forgejo `origin/main`).
Дата/время сверки: 2026-11-20T00:22Z UTC.

## Решение

**BLOCKED — входные свидетельства не выданы.** Запись в кластер и registry не выполнялась;
workflow/dispatch не запускался; образ не публиковался; Secret не создавался; значения
ключей не извлекались; cluster-wide изменения не выполнялись. Это ответ на наряд #42
(запрос входов), а не повтор предыдущего preflight #40.

По каждому условию наряда ниже: источник, метод проверки, результат и недостающий вход
с указанием, кто его предоставляет. Внутренние идентификаторы и учётные данные не
приводятся.

---

## 1. Application image: verified digest + provenance

| Поле | Значение |
|---|---|
| Источник | владелец сборки (канал GitHub Actions release → `ghcr.io/dedvmedved-dot/otus-diplom-portal`, private) |
| Метод проверки | cosign keyless verify с identity `https://github.com/dedvmedved-dot/otus-diplom/.github/workflows/p8c-portal-release.yml@refs/heads/main` и issuer `https://token.actions.githubusercontent.com`; SLSA provenance v0.2 + SPDX SBOM, связывающие digest с source `d22aa8f`; сверка registry bytes (manifest + Docker-Content-Digest) |
| Результат | **BLOCKED** — verified application digest + provenance отсутствуют |
| Недостающий вход | существующий immutable application image по digest + ссылка на доверенный run + проверяемая provenance (cosign/SBOM), связывающая digest с `d22aa8f`; ЛИБО письменное решение о канале сборки/публикации |
| Кто предоставляет | владелец сборки |

Свежие проверки (2026-11-20T00:2x UTC):

- GitHub `.github/workflows/` → `Not Found` (workflow не опубликован; в репозитории есть
  только template `portal/tools/p8c-portal-release.yml.template`, публикация — действие
  владельца через GitHub UI).
- GitHub releases → `0`; GitHub Actions runs → `total_count: 0`.
- `portal/manifests/deployment.yaml` строки 33 и 173 — placeholder
  `REPLACE_WITH_VERIFIED_DIGEST` (реальный digest никогда не закреплялся).
- GHCR `ghcr.io/v2/dedvmedved-dot/otus-diplom-portal/...` анонимно → HTTP 401
  (private или отсутствует — без авторизации неразличимо; 401 НЕ доказывает отсутствия
  образа, но и существования digest не доказывает).
- GitHub `main` = `de9e22b501320b0e23c75038e343963891c80657` — на 1 docs-коммит впереди
  `d22aa8f` (`ahead_by: 1`). Сборка по наряду должна фиксироваться на source `d22aa8f`;
  расхождение фиксируется для решения владельца/архитектора о точном ref.

Примечание: seed-образ, тег или хеш файла НЕ подходят (прямое требование наряда) —
нужен именно verified application digest + provenance, привязанные к `d22aa8f`.

## 2. Независимый версионированный эталон CA и UID кластера OTUS

| Поле | Значение |
|---|---|
| Источник | владелец OTUS |
| Метод проверки | сверка endpoint / CA / UID кластера с независимым версионированным эталоном (не по имени current-context) |
| Результат | **BLOCKED** — версионированный эталон CA и UID отсутствует; endpoint сверялся ранее |
| Недостающий вход | независимый версионированный эталон CA и UID (ссылка на ревизию + результат сверки, без значений) |
| Кто предоставляет | владелец OTUS |

Endpoint кластера сверялся ранее (совпадает с доверенной инвентаризацией). Для CA и UID
независимого версионированного эталона в доверенных источниках
(`docs/p0/infrastructure-passport.md`, `inventory/hosts.yaml`) нет — значение и ревизия
эталона должны быть выданы владельцем OTUS. Значения CA/UID и их производные не
публикуются.

## 3. Подтверждение pull-доступа для workload

| Поле | Значение |
|---|---|
| Источник | владелец registry |
| Метод проверки | подтверждение существующего pull-доступа workload к private `ghcr.io/dedvmedved-dot/otus-diplom-portal` |
| Результат | **BLOCKED** — pull-доступ не подтверждён |
| Недостающий вход | подтверждение существующего pull-доступа для workload (без извлечения значений ключей) |
| Кто предоставляет | владелец registry |

GHCR анонимно → HTTP 401 (private или отсутствует). Pull secret
`portal-registry-pull` в namespace `portal` отсутствует (установлено в пред. preflight);
токен инженера для проверки registry отсутствует. Secret инженером НЕ создаётся (запрет
наряда), значения ключей не извлекаются. 401 не доказывает отсутствия образа, но
существование pull-доступа не доказано.

## 4. Offline diff (Job + Deployment — один verified digest)

| Поле | Значение |
|---|---|
| Результат | **BLOCKED** — offline diff не готовится: verified digest отсутствует, placeholder нельзя заменять выдуманным digest |
| Условие | Job и Deployment используют один verified digest, без placeholder (не применяется) |

---

## Запрос владельцу (ожидаемое решение)

1. **Канал сборки/публикации.** Опубликовать `p8c-portal-release.yml` в
   `.github/workflows/` на GitHub и выполнить dispatch с typed release gate
   (single-attempt, `source_sha=d22aa8f...`), ЛИБО выдать существующий verified
   application digest + provenance (SBOM/SLSA/cosign), привязанные к `d22aa8f`.
2. **Эталон CA/UID.** Выдать независимый версионированный эталон CA и UID кластера OTUS
   (ссылка на ревизию, без значений).
3. **Pull-доступ.** Подтвердить существующий pull-доступ workload к private GHCR
   (или дать отдельное решение о механизме pull — imagePullSecret только как ref).

## Границы (соблюдены)

- Запись в кластер/registry: НЕ выполнялась. Workflow/dispatch: НЕ запускался. Образ: НЕ
  публиковался.
- Secret: НЕ создавался; значения ключей НЕ извлекались.
- Cluster-wide RBAC/Gateway/NetworkPolicy/Metrics Server/CNPG/operator: НЕ трогались.
- Применение тегов/placeholder: НЕ выполнялось.

## Приложение — свежие наблюдения (без секретов)

- source SHA: `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (`git rev-parse HEAD`, Forgejo main).
- GitHub `main`: `de9e22b501320b0e23c75038e343963891c80657` (ahead_by 1 vs `d22aa8f`).
- GitHub `.github/workflows`: `Not Found`.
- GitHub releases: `0`; Actions runs: `total_count: 0`.
- GHCR tags/manifest (anonymous): HTTP 401.
- `git grep -n REPLACE_WITH_VERIFIED_DIGEST -- portal/manifests/deployment.yaml` → строки 33, 173.
- Поиск версионированного эталона CA/UID в `docs/p0`, `inventory`: совпадений нет.
