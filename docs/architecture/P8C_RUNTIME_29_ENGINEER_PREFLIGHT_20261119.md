# P8C §6 — наряд #29: engineer preflight (до первой записи)

Роль: Implementation Engineer, assignee `hermes-5.187.1.37-engineer`.
Основание: наряд `docs/architecture/P8C_RUNTIME_29.md` @ `99f7881e6e82858fc96d58099c1c360c0fec9dad`
(решение владельца #29 — вариант А, тестовый контур OTUS).
Принятый source: `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (origin/main).
Принятая статическая матрица: `e135afaa81776832b0316cff12e1663e0a03d4b2`.
Окно: 2026-11-19 22:30–23:30 UTC (последние 15 минут — восстановление и контроль).
Время preflight: 2026-11-19T22:27Z UTC (до открытия окна).

## Решение

**NO-GO — запись не выполнялась.**

Фактический блокер: для принятого source отсутствует подтверждённый (verified)
application digest + provenance, а сам наряд прямо запрещает единственный легитимный
способ его получить — сборку/публикацию release (`Без … сборки/публикации release`).
Применение тегов или placeholder запрещено (`Не применять теги или placeholder`),
а в `portal/manifests/deployment.yaml` (строки 33 и 173) закреплён именно placeholder
`REPLACE_WITH_VERIFIED_DIGEST`. Обход не выполнялся; release не публиковался;
helper/pins не менялись.

Это тот же блокер, что зафиксирован Архитектором в предварительном результате
наряда (22:13 UTC): «нет подтверждённой пары target + deployable digest». Проверка
на стороне инженера его подтверждает и дополнительно снимает пункт «доступ к
контуру» — см. ниже.

## 1. Доступ к контуру OTUS — ПОДТВЕРЖДЁН (read-only)

Идентификация контура выполнена не по имени current-context, а сверкой с доверенной
инвентаризацией (`inventory/hosts.yaml`, `docs/p0/infrastructure-passport.md`).

| Параметр | Наблюдаемое | Сверка |
|---|---|---|
| Узел входа | node-01 (по инвентаризации `pak_portal`) | hostname совпадает |
| kubectl | v1.36.2 | `versions.lock` kubernetes 1.36.2 — совпадает |
| API endpoint | server конфигурации = API VIP из паспорта | совпадает |
| CA (обезличено) | SHA-256 fingerprint `BF:1E:36:EC:3B:1F:A6:AC:C8:8E:8D:C3:2D:83:46:6A:EA:3F:31:A3:7E:22:83:65:D2:71:E6:8C:6E:23:14:D9` | записан для сверки |
| UID кластера (обезличенный идентификатор) | kube-system UID `83a6fdee-dc2a-4441-b7fd-bb76bf6327ad` | записан (обезличенный id) |
| subject / разрешения | root@node-01, `KUBECONFIG=/etc/kubernetes/admin.conf`, context `kubernetes-admin@pak-portal` (cluster-admin) | фактическая учётка инженера; НЕ роль приложения |

Namespace `portal` существует (UID `396158dc-cc86-4f4e-b248-0b8832732b7f`,
создан 2026-10-19T22:05:56Z). В нём — только объекты CNPG/БД (`portal-db` 3/3,
primary `portal-db-2`; Services `portal-db-r/ro/rw`; secrets `portal-db-*`,
`portal-barman-s3-*`). Объектов Portal-приложения (Deployment/Job/Service
`portal`/`portal-db-metrics`, Gateway, HTTPRoute, Issuer, Certificate) НЕТ —
baseline подтверждает, что rollout Портала ранее не выполнялся.

Полный kubeconfig, CA-сертификат и значения секретов не публикуются.

## 2. Application digest + provenance — ОТСУТСТВУЮТ (блокер)

| Проверка | Результат |
|---|---|
| Поле образа Deployment | `ghcr.io/dedvmedved-dot/otus-diplom-portal@sha256:REPLACE_WITH_VERIFIED_DIGEST` (placeholder, строка 33) |
| Поле образа Job (migrate) | тот же placeholder (строка 173) — образы Job и Deployment формально одинаковы, но оба НЕ подтверждены |
| История git по `deployment.yaml` | реальный digest никогда не закреплялся (только placeholder) |
| Release/dispatch | не выполнялся (матрица §3: workflow не опубликован, dispatch не выполнен) |
| Provenance/SBOM/cosign для Portal-образа | отсутствуют в репозитории (имеющиеся provenance-артефакты относятся к CNPG/Barman/cert-manager/SeaweedFS и др., НЕ к Portal) |
| GHCR `dedvmedved-dot/otus-diplom-portal` | анонимный доступ 401 UNAUTHORIZED (приватный или отсутствует — различить без авторизации нельзя) |
| GitHub-токен инженера | `Bad credentials` — pull-доступ и существование digest проверить невозможно |
| Pull secret `portal-registry-pull` (требуется `imagePullSecrets` в deployment.yaml) | НЕ существует в namespace `portal` (NotFound) |

Вывод: подтверждённой пары «target + deployable digest» нет; provenance для
принятого source отсутствует; pull-доступ не доказан. Условие наряда «проверить
подписанный/проверенный application digest с привязкой к source, pull-доступ»
не выполнено.

## 3. Соответствие наряду и STOP

- «Нет … непроверенный target/digest … — остановка до записи» — выполнено: остановка
  ДО записи.
- «Не применять теги или placeholder» — применять нечего и нельзя; placeholder не
  применялся.
- «Без доказанного пути отката миграции не запускать Job» — Job миграции не запускался.
- «Без … сборки/публикации release» — release не собирался и не публиковался.
- Никакого blanket apply, cluster-wide RBAC/Gateway/NetworkPolicy/Metrics Server/
  CNPG/operator не трогались.

Запись (apply/rollout), строки матрицы §2.1–2.4 и rollback НЕ выполнялись ввиду
NO-GO. Остаточных изменений в кластере нет (все проверки read-only). Окно не
использовалось — запуск по таймеру не производился.

## 4. Необходимое для перехода к GO (вне полномочий инженера)

1. Выполнить release-сборку Portal (workflow/dispatch — сейчас ЗАПРЕЩЁН нарядом)
   и зафиксировать верифицированный digest + provenance (cosign/SBOM), привязанные
   к source `d22aa8f`.
2. Заменить placeholder в `portal/manifests/deployment.yaml` (строки 33, 173) на
   подтверждённый digest.
3. Создать pull secret `portal-registry-pull` в namespace `portal` и доказать
   pull-доступ к `ghcr.io/dedvmedved-dot/otus-diplom-portal`.
4. Зафиксировать новое окно (текущее окно 22:30–23:30 UTC пропущено по NO-GO).

## Приложение — исходные наблюдения (без секретов)

- source SHA: `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (`git rev-parse HEAD`).
- placeholder: `git grep -n REPLACE_WITH_VERIFIED_DIGEST -- portal/manifests/deployment.yaml`
  → строки 33 и 173.
- Forgejo releases: `[]`.
- GHCR anonymous tags: HTTP 401 `UNAUTHORIZED`.
- GitHub token check: HTTP 401 `Bad credentials`.
- `kubectl get secret portal-registry-pull -n portal`: NotFound.
- cluster UID: `83a6fdee-dc2a-4441-b7fd-bb76bf6327ad`.
- CA SHA-256 fingerprint: `BF:1E:36:EC:3B:1F:A6:AC:C8:8E:8D:C3:2D:83:46:6A:EA:3F:31:A3:7E:22:83:65:D2:71:E6:8C:6E:23:14:D9`.
