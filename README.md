# ПАК «Портал» — отказоустойчивый демонстрационный ПАК Kubernetes + LINSTOR/DRBD

## Назначение

Проект «Портал» — программно-аппаратный комплекс (ПАК), демонстрирующий
отказоустойчивую платформу на базе Kubernetes с репликацией блочных устройств
средствами DRBD/LINSTOR (Single-Primary), высокодоступной СУБД PostgreSQL под
управлением CloudNativePG, а также слоями наблюдаемости и резервного копирования.

Ключевые подсистемы:

- **Kubernetes** — оркестрация контейнеризованных сервисов (3 узла, HA);
- **DRBD / LINSTOR** — реплицируемое блочное хранилище (Single-Primary);
- **HA control plane** — kubeadm + kube-vip (API VIP), etcd 3 узла;
- **MetalLB** (L2) — внешние LoadBalancer-адреса;
- **Envoy Gateway** — внешний ingress (HTTPRoute);
- **PostgreSQL / CloudNativePG** — целевая СУБД (P8, ещё не развёрнута);
- **Observability / Backup** — Metrics Server 0.8.1 deployed и FINAL ACCEPTED; Velero 1.18.1 deployed; P7C-B2 runtime и reproducibility validation PASS, final Architect acceptance pending.

## Архитектурный baseline

Единственным авторитетным источником архитектуры является:

> **«Техническое решение ПАК Портал Kubernetes + DRBD/LINSTOR v4.0» (TR v4.0)**

Любое отклонение от TR v4.0 допускается только через утверждённый ADR.
Компоненты и их версии зафиксированы в [`versions.lock`](versions.lock).
GitHub `main` — Source of Truth.

## Управление проектом (governance)

| Роль | Ответственность |
| --- | --- |
| **Owner** | Владелец проекта, конечное решение по бюджету и политикам. |
| **Chief Architect** (ChatGPT) | Technical Authority, Task Author, External Auditor, Acceptance Authority, владелец Gate P0–P9. |
| **Hermes Implementation Engineer** | Implementation / DevOps / Evidence Collector. «Руки» Архитектора. |
| **Connector Audit** | Независимая проверка GitHub Архитектором. |

Полные операционные правила: [`docs/governance/project-governance.md`](docs/governance/project-governance.md).

## Текущий статус проекта

```text
P0  Passport / Precheck                                FINAL ACCEPTED
P1  Astra Linux / Network / Time                       FINAL ACCEPTED
P2  containerd / Kubernetes Packages                   FINAL ACCEPTED
P3  HA Control Plane / kube-vip / etcd                 FINAL ACCEPTED
P4  Calico / DNS / baseline policies                   FINAL ACCEPTED
P5  LINSTOR / DRBD                                     FINAL ACCEPTED
P6  MetalLB / Envoy Gateway                            FINAL ACCEPTED
P7  Observability / Backup                             IN PROGRESS
P8  PostgreSQL / Portal                                NOT AUTHORIZED
P9  Security / Failure / Performance / Restore / Acceptance
                                                        NOT AUTHORIZED
```

### Декомпозиция P7

```text
P7A   Observability / Backup Preflight                  FINAL ACCEPTED
P7B1  Kubelet Serving TLS Bootstrap / CSR Approval      FINAL ACCEPTED
P7B2  Metrics Server 0.8.1                              FINAL ACCEPTED
P7C   Velero / Backup                                   IN PROGRESS
  P7C-B1  CSI Snapshot Foundation                        FINAL ACCEPTED
  P7C-B2  Velero / S3 Foundation + CSI Data Movement     READY FOR ARCHITECT FINAL ACCEPTANCE
  P7C-C   Failure / Recovery Validation                  NOT AUTHORIZED
```

Переход между стадиями — только после явного решения Chief Architect:
`STAGE Px: PASSED / CONNECTOR VERIFIED / PROCEED TO Py`.

## Текущее техническое состояние

```text
Kubernetes:          1.36.2
nodes:               3/3 Ready
Astra Linux SE:      1.8.5.46
containerd:          2.3.3
kube-vip:            1.2.0
Calico:              3.32.0
DRBD:                9.3.2
LINSTOR:             1.33.2
LINSTOR CSI:         1.11.0
MetalLB:             0.16.1 (L2)
Envoy Gateway:       1.9.1
Metrics Server:      0.8.1 (deployed)
Velero:              1.18.1 (deployed)
Velero AWS plugin:   v1.14.2
SeaweedFS:           4.48
BSL:                 Available
Velero S3 prefix:    velero/
Combined-node taint: PreferNoSchedule
Helm:                4.1.3
```

## Текущее состояние блокеров и решений

```text
Observability:
  Kubelet serving TLS blocker closed by P7B1 (cluster-CA-trusted serving
  certificates via serverTLSBootstrap + controlled CSR approval).
  Metrics Server 0.8.1 deployed under P7B2 (secure kubelet TLS) and FINAL ACCEPTED.

Backup:
  SeaweedFS 4.48:              FINAL ACCEPTED for DEMO PAK
  S3 endpoint:                 https://s3-backup.demo-pak.test
  bucket:                      portal-velero-backup
  network path:                VLAN143
  private CA / TLS:            PASS
  versioning:                  enabled
  Object Lock:                 GOVERNANCE 7d
  lifecycle:                   30d
  CoreDNS private zone:        PASS
  CSI Snapshot:                PASS
  Velero:                      DEPLOYED (1.18.1)
  BSL:                         Available
  CSI Snapshot Data Movement:  PASS
  offsite restore:             PASS
  checksum:                    PASS
  P7C-B2:                      READY FOR ARCHITECT FINAL ACCEPTANCE

  Remaining P7 backup work:    P7C-C failure/recovery validation (NOT AUTHORIZED)
```

## Текущий verified state

```text
P0-P6:              FINAL ACCEPTED
P7A:                FINAL ACCEPTED
P7B1:               FINAL ACCEPTED
P7B2:               FINAL ACCEPTED
P7C-B1:             FINAL ACCEPTED
P7C-B2 runtime:     PASS / CONNECTOR VERIFIED
P7C-B2 canonical:   PASS / CONNECTOR VERIFIED
P7C-B2 reproducibility: PASS / CONNECTOR VERIFIED
P7C-B2 final:       READY FOR ARCHITECT FINAL ACCEPTANCE
P7C-C:              NOT AUTHORIZED
```

## Дорожная карта реализации Портала

Портал реализуется на **этапе P8 сразу после FINAL ACCEPTED этапа P7C**. Между
закрытием P7C и началом разработки Портала не вводится отдельный длительный
инфраструктурный этап.

Ключевой принцип: Портал — не декоративный web-интерфейс, а демонстрационная
оболочка над уже построенной платформой Kubernetes + LINSTOR/DRBD + Velero +
CloudNativePG. Первая рабочая версия Портала должна появиться в начале P8 и
развиваться параллельно с развёртыванием PostgreSQL и его backup/WAL-контура.

Утверждённая последовательность:

```text
P7C FINAL ACCEPTED
  -> P8A CloudNativePG / PostgreSQL foundation
  -> P8B PostgreSQL backup + WAL / S3
  -> P8C Portal MVP: backend + frontend
  -> P8D Portal integration with Kubernetes / storage / backup / observability
  -> P8E controlled demonstration scenarios
  -> P8F Portal HA / application failover
  -> P8G P8 acceptance
  -> P9 final security / failure / performance / restore acceptance
```

P8 остаётся `NOT AUTHORIZED` до отдельного решения Chief Architect после
завершения P7C.

CURRENT: P7C-B2 final Architect gate
NEXT:    P7C-C failure/recovery validation
AFTER P7C FINAL ACCEPTED: P8 begins, including early Portal implementation

Подробная дорожная карта:
[`docs/architecture/P8_PORTAL_IMPLEMENTATION_ROADMAP.md`](docs/architecture/P8_PORTAL_IMPLEMENTATION_ROADMAP.md).

## Рабочий процесс с репозиторием

- Source of Truth — этот репозиторий (`main`).
- Каждый логический этап — отдельный осмысленный commit; запрещены сообщения
  вида `fix`/`update`/`tmp`.
- Запрещён `git push --force` и переписывание опубликованной истории без
  отдельного указания.

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
