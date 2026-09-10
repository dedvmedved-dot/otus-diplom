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
- **Observability / Backup** — Metrics Server и Velero (P7, в работе).

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
P7B1  Kubelet Serving TLS Bootstrap / CSR Approval      IN PROGRESS — PENDING CHATGPT CONNECTOR ACCEPTANCE
P7B2  Metrics Server 0.8.1                              NOT AUTHORIZED
P7C   Velero / Backup Foundation                        NOT AUTHORIZED
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
Metrics Server (target): 0.8.1
Velero (target):         1.18.1
Helm:                4.1.3
```

## Текущее состояние блокеров и решений

```text
Observability:
  P7A доказала, что требуется remediation kubelet serving TLS (самоподписанные
  node-local сертификаты не доверялись cluster CA). P7B1 исправляет cluster-CA
  trust (serverTLSBootstrap + контролируемое одобрение serving CSR) перед
  развёртыванием Metrics Server.

Backup:
  заблокировано до получения параметров S3 (endpoint/bucket/region/object-lock/
  secret-ref), закрепления версии object-store plugin и выбора стратегии бэкапа
  (CSI snapshot API на кластере пока отсутствует).
```

## Текущий verified baseline

```text
Current accepted baseline before P7B1:
a5a97057cd7d83f93f612aeb1bfa997625b166ae

P7B1 implementation:
IN PROGRESS — pending Connector Audit
```

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
