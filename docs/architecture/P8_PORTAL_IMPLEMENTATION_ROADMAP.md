# P8 — дорожная карта реализации Портала

STATUS: ACCEPTED PLANNING DECISION  
ACCEPTED_BY: Chief Architect / Technical Authority  
DATE: 2026-10-19  
SCOPE: implementation sequencing for P8; this document does not authorize P8 runtime work.

## 1. Решение

Портал реализуется на этапе **P8**, сразу после завершения P7C и присвоения P7C
статуса **FINAL ACCEPTED / CONNECTOR VERIFIED**.

Между P7C и разработкой Портала не вводится отдельный длительный
инфраструктурный этап.

Первая работающая версия Портала должна появиться **в начале P8**, а не после
завершения всех работ с PostgreSQL. Portal MVP развивается параллельно с
доведением PostgreSQL/CloudNativePG и его backup/WAL-контура до целевого
состояния, как только определены стабильные интерфейсы приложения.

До отдельного решения Chief Architect:

```text
P8 = NOT AUTHORIZED
P9 = NOT AUTHORIZED
```

## 2. Роль Портала в ПАК

Портал — демонстрационная и операторская оболочка ПАК, а не отдельный
декоративный web-сайт.

Через него должно быть возможно наглядно показать состояние и работу уже
построенных подсистем:

- Kubernetes и HA control plane;
- LINSTOR / DRBD;
- persistent volumes и CSI snapshots;
- Velero / CSI Snapshot Data Movement;
- SeaweedFS S3 backup;
- CloudNativePG / PostgreSQL;
- наблюдаемость;
- контролируемые сценарии отказа и восстановления.

Портал не получает неограниченных административных полномочий.

Базовые ограничения:

- no cluster-admin for Portal;
- no direct BMC control from Portal;
- минимально необходимые RBAC/API;
- опасные действия только через специально разрешённый orchestration layer;
- destructive operations требуют отдельной scenario-level authorization.

## 3. Место P8 в общей дорожной карте

```text
P0-P6                 FINAL ACCEPTED
        |
P7                    IN PROGRESS
        |
P7C-B2                 runtime/reproducibility closure
        |
P7C-C                  failure / recovery validation
        |
P7C FINAL ACCEPTED
        |
        v
+--------------------------------------------------+
| P8 — PostgreSQL / CloudNativePG / Portal         |
+--------------------------------------------------+
        |
        +--> P8A PostgreSQL / CloudNativePG foundation
        |
        +--> P8B PostgreSQL backup + WAL / S3
        |
        +--> P8C Portal MVP
        |
        +--> P8D Platform integration
        |
        +--> P8E Demonstration scenarios
        |
        +--> P8F Portal HA / failover
        |
        +--> P8G P8 acceptance
        |
        v
P9 Security / Failure / Performance / Restore / Final Acceptance
```

Roadmap checkpoint at approval time:

```text
GitHub main before this roadmap commit:
16b666d39506d6c103be2746c045953c9815f7f6

P7C-B2-R2:
committed by Hermes; Chief Architect final Connector acceptance pending

Next after P7C-B2 acceptance:
P7C-C

Portal implementation:
starts in P8 immediately after P7C FINAL ACCEPTED
```

The checkpoint SHA above is historical context for this planning decision.
Later commits supersede the SHA but not the sequencing decision unless a new
Architect/Owner decision changes it.

## 4. P8A — CloudNativePG / PostgreSQL foundation

Цель — получить рабочую HA СУБД, которую Portal использует как штатный data/state
layer.

Planned baseline:

- CloudNativePG 1.29.1;
- PostgreSQL 17.10;
- persistent storage на LINSTOR/DRBD;
- HA/failover через CloudNativePG;
- Services и DNS;
- controlled credentials;
- readiness/liveness;
- минимальный schema/application contract для Portal.

Результат P8A:

```text
POSTGRESQL_HA = PASS
PORTAL_DB_ENDPOINT = READY
PORTAL_SCHEMA_CONTRACT = READY
```

## 5. P8B — PostgreSQL backup + WAL

Цель — закрыть отдельный backup-контур БД.

Целевая модель:

```text
CloudNativePG
  -> Barman
  -> S3
  -> SeaweedFS
```

Точные bucket/prefix и credentials утверждаются отдельным P8 Gate.

Необходимо доказать:

- base backup;
- continuous WAL archiving;
- целевой RPO;
- restore;
- point-in-time recovery, если он включён окончательным P8 design;
- data validation;
- отсутствие подмены backup обычной DRBD replication.

## 6. P8C — Portal MVP

Portal MVP начинается как можно раньше после появления стабильного P8A API/DB
контракта.

Минимальная рабочая версия должна включать:

### Frontend

- главную страницу состояния ПАК;
- состояние узлов;
- состояние основных workload/service;
- состояние storage;
- состояние backup;
- состояние PostgreSQL;
- состояние/историю демонстрационных сценариев.

### Backend/API

Backend агрегирует только разрешённую информацию из:

- Kubernetes API;
- Metrics Server / доступных platform metrics;
- Velero API;
- Kubernetes storage objects;
- CloudNativePG objects;
- безопасных adapters для LINSTOR/DRBD state, если они потребуются.

Portal backend не получает прямой неограниченный shell/root-доступ к узлам.

Результат P8C:

```text
PORTAL_UI = RUNNING
PORTAL_API = RUNNING
PORTAL_DB = CONNECTED
PLATFORM_STATUS = VISIBLE
```

## 7. P8D — интеграция Portal с платформой

После MVP добавляются проверяемые интеграции.

Минимальный целевой набор:

- Kubernetes Nodes;
- Pods/workloads;
- Services/Gateway;
- PVC/PV/VolumeSnapshot;
- LINSTOR/DRBD health summary;
- Velero BSL/Backup/Restore status;
- CloudNativePG cluster/instance state;
- platform metrics;
- event timeline.

Интеграции read-only по умолчанию.

Любая mutation-функция должна иметь отдельный разрешённый API и минимальный
RBAC.

## 8. P8E — контролируемые демонстрационные сценарии

Portal должен демонстрировать отказоустойчивость ПАК без выдачи пользователю
неограниченного доступа к инфраструктуре.

Целевая модель:

```text
Portal
  -> Scenario API
  -> allow-listed scenario
  -> controlled orchestrator
  -> Kubernetes/platform action
  -> evidence/events
  -> recovery
  -> result shown in Portal
```

Классы сценариев, которые могут быть отдельно утверждены:

- restart application pod;
- loss/recreation of application instance;
- storage replica/failover demonstration;
- database leader failover;
- backup creation;
- restore from backup;
- service recovery observation.

Само перечисление сценария в этой дорожной карте не является разрешением на
destructive/failure execution.

## 9. P8F — HA и отказоустойчивость Портала

Проверить:

- несколько Portal replicas, если это требуется финальной архитектурой;
- restart/re-scheduling;
- node loss;
- backend reconnection;
- PostgreSQL failover;
- сохранение прикладного состояния;
- отсутствие single point of failure, противоречащего демонстрационной цели ПАК.

## 10. P8G — приёмка P8

P8 завершается после доказательства полного тракта:

```text
User
 -> Envoy Gateway
 -> Portal frontend
 -> Portal backend
 -> PostgreSQL / platform APIs
 -> storage / backup / observability
 -> controlled scenario
 -> failure/recovery
 -> correct Portal state
```

Минимальные критерии:

- Portal доступен через утверждённый ingress;
- Portal использует HA PostgreSQL;
- storage работает через утверждённый LINSTOR/DRBD baseline;
- DB backup/WAL и restore доказаны;
- Portal отображает фактическое состояние платформы;
- разрешённые сценарии выполняются через ограниченный orchestration layer;
- Portal не имеет cluster-admin;
- Portal не управляет BMC напрямую;
- секреты не находятся в Git;
- после отказов Portal возвращается в рабочее состояние;
- evidence сохранён.

## 11. P9 после реализации Портала

P9 не используется для базовой разработки Portal.

К началу P9 Portal уже должен быть функционально завершён в P8.

P9 предназначен для интегральной финальной проверки:

- security;
- отказоустойчивость;
- производительность;
- backup/restore;
- failure scenarios;
- recovery;
- эксплуатационная воспроизводимость;
- финальная приёмка ПАК.

## 12. Зафиксированная последовательность

```text
CURRENT:
P8A CloudNativePG / PostgreSQL foundation

THEN:
P7C-B2 FINAL ACCEPTED
P7C-C
P7C FINAL ACCEPTED

THEN IMMEDIATELY:
P8A + early P8C preparation
P8B
P8C Portal MVP
P8D
P8E
P8F
P8G

THEN:
P9

END:
PAK PORTAL FINAL ACCEPTED
```

## 13. Правило изменения дорожной карты

Эта последовательность является утверждённым planning baseline.

Она может быть изменена только явным решением Chief Architect/Owner с
фиксацией причины в текущих architecture/governance документах или ADR, если
изменение затрагивает архитектуру.
