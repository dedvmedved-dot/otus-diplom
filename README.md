# ПАК «Портал» — отказоустойчивый демонстрационный ПАК Kubernetes + LINSTOR/DRBD

## Назначение

Проект «Портал» — программно-аппаратный комплекс (ПАК), демонстрирующий
отказоустойчивую платформу на базе Kubernetes с репликацией блочных устройств
средствами DRBD/LINSTOR (Single-Primary) и высокодоступной СУБД PostgreSQL под
управлением CloudNativePG.

## Архитектурный baseline

Единственным авторитетным источником архитектуры является:

> **«Техническое решение ПАК Портал Kubernetes + DRBD/LINSTOR v4.0» (TR v4.0)**

Любое отклонение от TR v4.0 допускается только через утверждённый ADR
(см. правило ниже). Компоненты и их версии зафиксированы в
[`versions.lock`](versions.lock).

## Управление проектом (governance)

| Роль | Ответственность |
| --- | --- |
| **Owner** | Владелец проекта, конечное решение по бюджету и политикам. |
| **Chief Architect** (ChatGPT) | Technical Authority, Task Author, External Auditor, Acceptance Authority, владелец Gate P0–P9. |
| **Hermes Implementation Engineer** (Claude Opus 4.8) | Implementation / DevOps / Evidence Collector. «Руки» Архитектора. |
| **Connector Audit** | Независимая проверка GitHub Архитектором. |

Полные операционные правила: [`docs/governance/project-governance.md`](docs/governance/project-governance.md).

## Последовательность Gate P0–P9

```text
P0  Passport / Precheck
P1  Astra Linux / Network / Time
P2  containerd / Kubernetes Packages
P3  HA Control Plane / kube-vip / etcd
P4  Calico / DNS / baseline policies
P5  LINSTOR / DRBD
P6  MetalLB / Envoy Gateway
P7  Observability / Backup
P8  PostgreSQL / Portal
P9  Security / Failure / Performance / Restore / Acceptance
```

Переход между стадиями возможен только после явного решения Chief Architect:
`STAGE Px: PASSED / CONNECTOR VERIFIED / PROCEED TO Py`.

## Текущий статус проекта

```text
TASK-001: PASSED / CONNECTOR VERIFIED
P0: IN PROGRESS — PREPARATION ONLY
P1-P9: NOT AUTHORIZED
```

Текущая стадия: **P0 (подготовка репозитория и preflight)**. P0 Gate **не пройден**.

## Рабочий процесс с репозиторием

- Source of Truth — этот репозиторий (`main`).
- Начальный baseline создаётся прямым коммитом в `main` (разовая авторизация TASK-002).
- Дальнейшая работа — через контролируемые задачные ветки, если Архитектор не укажет иное.
- Каждый логический этап — отдельный осмысленный commit; запрещены сообщения вида `fix`/`update`/`tmp`.
- Запрещён `git push --force` и переписывание опубликованной истории без отдельного указания.

## Правило Evidence-first

Заявление «работает» доказательством не является. Каждое существенное
утверждение сопровождается фактическим evidence (см. [`evidence/`](evidence/)).
Результаты фиксируются честно: `FAIL` / `INCOMPLETE` / `NOT VERIFIED`.
Фальсификация evidence запрещена. Итоговые статусы `PASSED` / `CONNECTOR VERIFIED`
присваивает только Chief Architect.

## Запрет секретов

Секреты (пароли, токены, ключи, kubeconfig с секретами, BMC/S3 credentials и т.п.)
запрещено помещать в Git в любом виде. Используются secret references,
переменные окружения и защищённые secret stores. См. [`.gitignore`](.gitignore).

## Изменение архитектуры — только через ADR

При обнаружении невозможности реализовать TR v4.0 Hermes готовит `ADR-PROPOSAL`
(статус `PROPOSED / NOT APPROVED`) и не начинает реализацию до решения Архитектора.

## Правило исправления документации (max 3)

На чисто оформительские (косметические/редакторские) правки документации
допускается максимум 3 задания. Технические дефекты документации (неверная
команда, IP, disk ID, procedure restore и т.п.) под лимит не попадают.
Счётчик: см. [`docs/backlog/documentation-backlog.md`](docs/backlog/documentation-backlog.md).

```text
Documentation Correction Task: 0/3
```
