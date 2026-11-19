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

## 1. Доступ и идентичность контура OTUS (read-only)

Идентификация контура выполнена не по имени current-context, а сверкой с доверенной
инвентаризацией. Доступ и идентичность — разные проверки; совпадение имени узла и
версии kubectl само по себе не идентифицирует кластер.

Доступ подтверждён: узел входа совпадает с инвентаризацией
`inventory/hosts.yaml` @ `82e20a2ea997c0f046a0c76600e99a6ecd97f66e`; kubectl
v1.36.2 совпадает с `versions.lock` @ `edb9ef8a5ca4fe21ee397cabbd008befcf177e17`.

Идентичность — сверка endpoint / CA / UID с независимым доверенным эталоном:

| Параметр | Статус | Независимый доверенный эталон (ревизия, без значения) |
|---|---|---|
| API endpoint | **проверено** | совпадает с VIP из `docs/p0/infrastructure-passport.md` @ `9c894af2dda4695489905df801904b9d04f02d93` |
| CA | **не проверено** | эталон отсутствует — в названных источниках (`inventory/hosts.yaml`, `docs/p0/infrastructure-passport.md`) значение CA не найдено |
| UID кластера (kube-system) | **не проверено** | эталон отсутствует — в названных источниках значение UID не найдено |

Блокеры (остаются): для CA и UID независимого доверенного эталона нет, поэтому
«записано» ≠ «проверено»; сверка идентичности по CA/UID не закрыта. Значения
CA/UID и их производные не публикуются.

Роль учётки контроля: cluster-admin (инженер, read-only); это роль контроля, а НЕ
роль приложения. Kubeconfig, CA-сертификат, отпечаток и значения секретов не
публикуются.

Namespace `portal` существует (создан 2026-10-19T22:05:56Z). В нём — только
объекты CNPG/БД (`portal-db` 3/3, primary `portal-db-2`; Services `portal-db-r/ro/rw`;
secrets `portal-db-*`, `portal-barman-s3-*`). Объектов Portal-приложения
(Deployment/Job/Service `portal`/`portal-db-metrics`, Gateway, HTTPRoute, Issuer,
Certificate) НЕТ — baseline подтверждает, что rollout Портала ранее не выполнялся.

## 2. Application digest + provenance — ОТСУТСТВУЮТ (блокер)

| Проверка | Результат |
|---|---|
| Поле образа Deployment | `ghcr.io/dedvmedved-dot/otus-diplom-portal@sha256:REPLACE_WITH_VERIFIED_DIGEST` (placeholder, строка 33) |
| Поле образа Job (migrate) | тот же placeholder (строка 173) — образы Job и Deployment формально одинаковы, но оба НЕ подтверждены |
| История git по `deployment.yaml` | реальный digest никогда не закреплялся (только placeholder) |
| Release/dispatch (область наблюдения = Forgejo) | releases/tags/Actions runs пусты; workflow не опубликован; dispatch по наряду не выполнялся |
| Provenance/SBOM/cosign для Portal-образа | отсутствуют в репозитории (имеющиеся provenance-артефакты относятся к CNPG/Barman/cert-manager/SeaweedFS и др., НЕ к Portal) |
| GHCR `dedvmedved-dot/otus-diplom-portal` | анонимный доступ 401 UNAUTHORIZED (приватный или отсутствует — различить без авторизации нельзя) |
| GitHub-токен инженера | `Bad credentials` — pull-доступ и существование digest проверить невозможно |
| Pull secret `portal-registry-pull` (требуется `imagePullSecrets` в deployment.yaml) | НЕ существует в namespace `portal` (NotFound) |

Вывод: подтверждённой пары «target + deployable digest» нет; provenance для
принятого source отсутствует; pull-доступ не доказан. Условие наряда «проверить
подписанный/проверенный application digest с привязкой к source, pull-доступ»
не выполнено.

Ограничение вывода о release: наблюдение ограничено Forgejo
(releases/tags/Actions runs). Внешний GitHub/GHCR не является предметом аудита —
HTTP 401 не доказывает ни отсутствия пакета, ни отсутствия запуска release.

## 3. Соответствие наряду и STOP

- «Нет … непроверенный target/digest … — остановка до записи» — выполнено: остановка
  ДО записи.
- «Не применять теги или placeholder» — применять нечего и нельзя; placeholder не
  применялся.
- «Без доказанного пути отката миграции не запускать Job» — Job миграции не запускался.
- «Без … сборки/публикации release» — release не собирался и не публиковался
  (в области наблюдения Forgejo; внешние registry не аудировались).
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
