# P8C Forgejo build spec — результат доработки по решению #52 (review a5f0e759)

Run: 2026-11-20T08:18:30Z UTC. Исполнитель: Hermes engineer.
Source SHA (pinned): `d22aa8f1170deaf09580518916ea02c7c4d8bfba`
Tools pin (P0 placeholder): `<FORGEJO_TOOLS_SHA>`
Rework head (этот коммит ветки): `97577abca70bae67f5a0f3430ac1ae76cb6ab775`

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
| 01-syntax-check.txt | офлайн-проверка синтаксиса workflow-шаблона (2 jobs, 41 выражение) |
| 02-unit-tests.txt | юнит-тесты gate: 37/37 PASS |
| 03-integration-harness.txt | офлайн-интеграционный harness: 23/23 PASS |
| 04-source-pins.txt | source-дерево (d22aa8f, неизменно) + tools-дерево (pin placeholder) |
| result.md | этот файл |

Результаты:

```text
01 SYNTAX      = VERIFIED   (YAML well-formed; 2 jobs; 41 expressions balanced)
02 UNIT        = 37/37 PASS (owner gate / inventory / registry / statement / lock pair)
03 INTEGRATION = 23/23 PASS (positive scratch-lock + 4 blocking-discrepancy classes)
04 PINS        = зафиксированы (source d22aa8f; tools <FORGEJO_TOOLS_SHA>)
```

Закрываемые блокирующие расхождения (#52):

1. **Owner gate** — `release_gate` обязателен (`required: true`), проверяется
   ПЕРВЫМ шагом release-job (до credentials/build/push/sign). Офлайн-отказы:
   отсутствующий / просроченный / чужой допуск — PASS.
2. **Source/tools** — два независимых pin и две независимые checkout-директории;
   инвентаризация файлов по деревьям; подмена source новым HEAD / пронос
   tools-файла в source — отказ.
3. **Trusted registry** — manifest байтово проверяется только с доверенного
   registry; чужое назначение отклоняется ДО сетевого запроса (mock transport
   не вызван); credentials не передаются постороннему host.
4. **Verified statement** — gate читает подписанный проверенный in-toto statement
   того же run (`cosign verify-attestation`), не локальный predicate; сверяются
   issuer/identity/тип/image/digest/source/workflow SHA/run. Отказы: нет verified
   результата, другой run/registry, несвязанный subject, подмена predicate.

Lock: `registry`+`digest` записываются одной парой в `portal/versions.lock:image`
только при `inputs.apply_lock == true`; реальный lock не менялся.

Границы #54 соблюдены: CI не запускался, build/push/sign/attest не выполнялись,
реальные секреты не запрашивались, стенд не затрагивался, настоящие locks не
менялись. Фактическая сборка не выполнялась — digest остаётся NOT_VERIFIED.
