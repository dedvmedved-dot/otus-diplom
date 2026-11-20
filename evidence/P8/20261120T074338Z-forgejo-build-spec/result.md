# P8C Forgejo Actions build spec — результат локальных проверок

Run: 2026-11-20T07:48Z UTC. Исполнитель: Hermes engineer.
Source SHA (pinned): `d22aa8f1170deaf09580518916ea02c7c4d8bfba`
Tree SHA: `72fbe02838850c1ed9576ef73c263481fe607322`

Статус:

```text
PREPARATION = COMPLETE (REVIEW_READY, offline)
APPLICATION_DIGEST / SLSA_PROVENANCE = NOT_VERIFIED
WORKFLOW_PUBLICATION / DISPATCH / BUILD / PUSH / SIGN / ATTEST = NOT_AUTHORIZED
LOCK_UPDATE = NOT_PERFORMED
```

Состав каталога:

| Файл | Содержимое |
|---|---|
| 01-syntax-check.txt | офлайн-проверка синтаксиса workflow-шаблона (check_forgejo_workflow_syntax.py) |
| 02-negative-check.txt | отрицательная проверка lock-update gate (test_forgejo_lock_gate.py) |
| 03-oidc-discovery.txt | read-only discovery OIDC issuer Forgejo |
| 04-source-pins.txt | blob/sha256/size закреплённых путей по дереву d22aa8f |
| result.md | этот файл |

Результаты:

```text
01 SYNTAX      = VERIFIED   (YAML well-formed; 3 jobs; 22 expressions balanced)
02 NEGATIVE    = 11/11 PASS (HARNESS_EXIT=0): несовпадение SHA / отсутствие
                 provenance / тег вместо digest => lock update НЕ разрешён
03 OIDC issuer = https://git.aiopslab.online (HTTP 200, read-only)
04 PINS        = зафиксированы (см. файл)
```

Границы #49 соблюдены: CI не запускался, образы не публиковались, секреты не
запрашивались, стенд не затрагивался. Фактическая сборка не выполнялась —
digest остаётся NOT_VERIFIED.
