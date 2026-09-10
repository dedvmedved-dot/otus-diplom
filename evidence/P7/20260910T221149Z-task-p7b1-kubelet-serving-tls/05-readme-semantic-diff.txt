7,8c7,18
< средствами DRBD/LINSTOR (Single-Primary) и высокодоступной СУБД PostgreSQL под
< управлением CloudNativePG.
---
> средствами DRBD/LINSTOR (Single-Primary), высокодоступной СУБД PostgreSQL под
> управлением CloudNativePG, а также слоями наблюдаемости и резервного копирования.
> 
> Ключевые подсистемы:
> 
> - **Kubernetes** — оркестрация контейнеризованных сервисов (3 узла, HA);
> - **DRBD / LINSTOR** — реплицируемое блочное хранилище (Single-Primary);
> - **HA control plane** — kubeadm + kube-vip (API VIP), etcd 3 узла;
> - **MetalLB** (L2) — внешние LoadBalancer-адреса;
> - **Envoy Gateway** — внешний ingress (HTTPRoute);
> - **PostgreSQL / CloudNativePG** — целевая СУБД (P8, ещё не развёрнута);
> - **Observability / Backup** — Metrics Server и Velero (P7, в работе).
16,18c26,28
< Любое отклонение от TR v4.0 допускается только через утверждённый ADR
< (см. правило ниже). Компоненты и их версии зафиксированы в
< [`versions.lock`](versions.lock).
---
> Любое отклонение от TR v4.0 допускается только через утверждённый ADR.
> Компоненты и их версии зафиксированы в [`versions.lock`](versions.lock).
> GitHub `main` — Source of Truth.
26c36
< | **Hermes Implementation Engineer** (Claude Opus 4.8) | Implementation / DevOps / Evidence Collector. «Руки» Архитектора. |
---
> | **Hermes Implementation Engineer** | Implementation / DevOps / Evidence Collector. «Руки» Архитектора. |
31c41
< ## Последовательность Gate P0–P9
---
> ## Текущий статус проекта
34,42c44,52
< P0  Passport / Precheck
< P1  Astra Linux / Network / Time
< P2  containerd / Kubernetes Packages
< P3  HA Control Plane / kube-vip / etcd
< P4  Calico / DNS / baseline policies
< P5  LINSTOR / DRBD
< P6  MetalLB / Envoy Gateway
< P7  Observability / Backup
< P8  PostgreSQL / Portal
---
> P0  Passport / Precheck                                FINAL ACCEPTED
> P1  Astra Linux / Network / Time                       FINAL ACCEPTED
> P2  containerd / Kubernetes Packages                   FINAL ACCEPTED
> P3  HA Control Plane / kube-vip / etcd                 FINAL ACCEPTED
> P4  Calico / DNS / baseline policies                   FINAL ACCEPTED
> P5  LINSTOR / DRBD                                     FINAL ACCEPTED
> P6  MetalLB / Envoy Gateway                            FINAL ACCEPTED
> P7  Observability / Backup                             IN PROGRESS
> P8  PostgreSQL / Portal                                NOT AUTHORIZED
43a54
>                                                         NOT AUTHORIZED
46c57,66
< Переход между стадиями возможен только после явного решения Chief Architect:
---
> ### Декомпозиция P7
> 
> ```text
> P7A   Observability / Backup Preflight                  FINAL ACCEPTED
> P7B1  Kubelet Serving TLS Bootstrap / CSR Approval      IN PROGRESS — PENDING CHATGPT CONNECTOR ACCEPTANCE
> P7B2  Metrics Server 0.8.1                              NOT AUTHORIZED
> P7C   Velero / Backup Foundation                        NOT AUTHORIZED
> ```
> 
> Переход между стадиями — только после явного решения Chief Architect:
49c69
< ## Текущий статус проекта
---
> ## Текущее техническое состояние
52,54c72,85
< TASK-001: PASSED / CONNECTOR VERIFIED
< P0: IN PROGRESS — PREPARATION ONLY
< P1-P9: NOT AUTHORIZED
---
> Kubernetes:          1.36.2
> nodes:               3/3 Ready
> Astra Linux SE:      1.8.5.46
> containerd:          2.3.3
> kube-vip:            1.2.0
> Calico:              3.32.0
> DRBD:                9.3.2
> LINSTOR:             1.33.2
> LINSTOR CSI:         1.11.0
> MetalLB:             0.16.1 (L2)
> Envoy Gateway:       1.9.1
> Metrics Server (target): 0.8.1
> Velero (target):         1.18.1
> Helm:                4.1.3
57c88,111
< Текущая стадия: **P0 (подготовка репозитория и preflight)**. P0 Gate **не пройден**.
---
> ## Текущее состояние блокеров и решений
> 
> ```text
> Observability:
>   P7A доказала, что требуется remediation kubelet serving TLS (самоподписанные
>   node-local сертификаты не доверялись cluster CA). P7B1 исправляет cluster-CA
>   trust (serverTLSBootstrap + контролируемое одобрение serving CSR) перед
>   развёртыванием Metrics Server.
> 
> Backup:
>   заблокировано до получения параметров S3 (endpoint/bucket/region/object-lock/
>   secret-ref), закрепления версии object-store plugin и выбора стратегии бэкапа
>   (CSI snapshot API на кластере пока отсутствует).
> ```
> 
> ## Текущий verified baseline
> 
> ```text
> Current accepted baseline before P7B1:
> a5a97057cd7d83f93f612aeb1bfa997625b166ae
> 
> P7B1 implementation:
> IN PROGRESS — pending Connector Audit
> ```
62,65c116,119
< - Начальный baseline создаётся прямым коммитом в `main` (разовая авторизация TASK-002).
< - Дальнейшая работа — через контролируемые задачные ветки, если Архитектор не укажет иное.
< - Каждый логический этап — отдельный осмысленный commit; запрещены сообщения вида `fix`/`update`/`tmp`.
< - Запрещён `git push --force` и переписывание опубликованной истории без отдельного указания.
---
> - Каждый логический этап — отдельный осмысленный commit; запрещены сообщения
>   вида `fix`/`update`/`tmp`.
> - Запрещён `git push --force` и переписывание опубликованной истории без
>   отдельного указания.
85,95d138
< 
< ## Правило исправления документации (max 3)
< 
< На чисто оформительские (косметические/редакторские) правки документации
< допускается максимум 3 задания. Технические дефекты документации (неверная
< команда, IP, disk ID, procedure restore и т.п.) под лимит не попадают.
< Счётчик: см. [`docs/backlog/documentation-backlog.md`](docs/backlog/documentation-backlog.md).
< 
< ```text
< Documentation Correction Task: 0/3
< ```
