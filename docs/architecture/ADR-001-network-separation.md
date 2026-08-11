# ADR-001 — Разделение сетей: отдельный bond для DRBD

**Статус:** APPROVED (ARCHITECT DECISION TASK-007/P1)
**Дата:** 2026-08-11
**Контекст:** TASK-007 / P1 — распределение портов X710 10GbE

---

## Контекст

На каждом узле ПАК (node-01, node-02, node-03) доступно 4 порта Intel X710 10GbE и 4 порта Intel I350 1GbE. Целевая архитектура (ТР v4.0) требует разделения Management/API и DRBD replication сетей.

## Варианты

### A — Всё на одном bond
```
bond0 (2 порта) → все VLAN (140/141/700)
+ просто
− Management и DRBD делят полосу
− нет изоляции failure domains
```

### B — Отдельный bond для DRBD ✅ ВЫБРАН
```
bond0 (ens2f0+f1, 2 порта) → Management/API/Backup/VLAN700
bond1 (ens2f2+f3, 2 порта) → DRBD replication ONLY
+ физическая изоляция DRBD трафика
+ предсказуемая полоса для репликации
+ независимые failure domains
```

### C — Один 4-портовый bond
```
bond0 (4 порта) → всё
+ максимальная агрегированная полоса 40 Гбит/с
− общий failure domain для Management и DRBD
− отклонено
```

## Решение

**Вариант B — APPROVED.**

```
bond0 = ens2f0 + ens2f1:
  VLAN 140 — Management / Kubernetes API (172.30.140.0/24)
  VLAN 143 — Backup (172.30.143.0/24)
  VLAN 700 — временный management (192.168.194.0/24)

bond1 = ens2f2 + ens2f3:
  VLAN 141 — DRBD/LINSTOR replication ONLY (172.30.141.0/24)
  GATEWAY: NONE (directly connected)

BMC: выделенный физический интерфейс (VLAN 142, out-of-band)
I350 1GbE (ens4f0-3): RESERVED / UNUSED
```

## Bond mode

- Предпочтительный: **802.3ad (LACP)** — при поддержке MLAG/MC-LAG на коммутаторах
- Fallback: **active-backup** — если LACP невозможен
- **balance-rr — ЗАПРЕЩЁН** как целевой режим

## VLAN 700

Сохранить как fallback. Не удалять до полной проверки VLAN 140/141 на всех трёх узлах.

## Риски

- Требуется настройка LACP на коммутаторах для bond0 и bond1
- При отсутствии MLAG — падение одного коммутатора = потеря bond
- VLAN 140/141 не проходят через коммутаторы на момент решения

## Rollback

Вернуться к VLAN 700 как единственной рабочей сети. Все настройки обратимы через NMCLI.

## Применяется к

- node-01 (YADRO S/N 0112220E3D)
- node-02 (YADRO S/N 7490778100035)
- node-03 (после ремонта — та же конфигурация)
