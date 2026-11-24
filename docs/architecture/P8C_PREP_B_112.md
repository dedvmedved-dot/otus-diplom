# P8C #112 — проверка готовности первого B: нехватка входов (SAN, admission)

Статус: `BLOCKED — NOT_READY_FOR_DISPATCH` (нехватка данных, подготовка НЕ завершена).
Роль: Implementation Engineer (Hermes). Наряд — [issue #112](https://git.aiopslab.online/aiopslab/otus-diplom/issues/112),
решение архитектора `4f25ff121c3178e3eb31160e61a84eef0937c84b`
(`docs/architecture/P8C_B_HANDOFF_111.md`).

## Основание

- [Ответ владельца 24.11.2026 09:16 UTC](https://git.aiopslab.online/aiopslab/otus-diplom/issues/68#issuecomment-6826):
  допуск **B** (`apply_lock=false`), канал сборки Forgejo Actions → Forgejo registry,
  источник `PINNED_SOURCE_SHA`, pull — runner-токеном. «Параметры публикации из §2 листа
  решения — подтверждаю как есть».
- Исходная точка: [PR #102](https://git.aiopslab.online/aiopslab/otus-diplom/pulls/102),
  tip `46e77bc9a31e43c333b73337bd928bc424e046b8`.
- Офлайн-приёмка #108: `220028f6525d04f29857f775bf1177d1cc08551b`
  (`docs/architecture/P8C_REVIEW_108.md`).

## Результат проверок (наряд #112 п. 1)

Проверено наличие явных подтверждений владельца до выдачи задания runner. Секреты и
токены в этот отчёт не включались.

| Контроль | Результат |
|---|---|
| Явное подтверждение владельцем точного OIDC SAN (certificate identity / `WORKFLOW_IDENTITY`) | **ОТСУТСТВУЕТ** — значение остаётся плейсхолдером `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` (workflow PR #102 и `forgejo_lock_gate.py` L102–103) |
| Независимое свидетельство доверия issuer/identity (CA-доверие, audience, trust roots, привязка к workflow) | **ОТСУТСТВУЕТ** — issuer `https://git.aiopslab.online/api/actions` подтверждён только по исходникам/дискавери (`routers/api/actions/id_token.go` + `/api/actions/.well-known/openid-configuration`), но CA-доверие/audience/trust roots владельцем не подтверждены |
| Подтверждение эксклюзивного admission-барьера до выдачи задания runner | **ОТСУТСТВУЕТ** — job `admission` (`runs-on: otus-diplom-admission`) fail-closed на `inputs.admission_confirmed`; выделенный label/runner и процедура закрытия/открытия выдачи на инстансе владельцем не подтверждены |

## Единый список нехватки данных

| # | Какой факт отсутствует | Кто подтверждает | Какой ответ нужен |
|---|---|---|---|
| 1 | Точное значение OIDC SAN — certificate identity (Forgejo id-token `sub`), которую `cosign verify`/`verify-attestation` сверяют по `--certificate-identity` | Владелец (`gitaiopslab`) | Точное значение SAN + привязка к одобренному workflow (заменить `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` на подтверждённое значение) |
| 2 | Независимое свидетельство доверия issuer/identity: CA-доверие к issuer `https://git.aiopslab.online/api/actions`, audience, trust roots | Владелец | Подтверждение trust-цепочки (CA → issuer → audience → workflow binding) и согласованные trust roots для sign/verify/verify-attestation |
| 3 | Эксклюзивный admission-барьер установлен ДО выдачи задания runner: выделенный runner/label `otus-diplom-admission` без других подходящих runners, закрытие выдачи, отсутствие активных/конкурирующих release-runs, подтверждённый gate PUT (201/204) возвращённого run id | Владелец | Подтверждение барьера (runner + процедура закрытия/открытия выдачи) — задаёт `inputs.admission_confirmed` |

## Почему общее согласие с §2 НЕ покрывает SAN

Ответ владельца подтверждает «Параметры публикации из §2» как есть. Но точный OIDC SAN
(certificate identity) **не входит в §2** — он описан в §1 листа решения
(`docs/architecture/P8C_OWNER_DECISION_67.md`, commit `09beada8…`) как «ожидаемая
certificate identity … **ещё НЕ проверена** — до первого реального подписанного запуска»,
и с review #95 заменён плейсхолдером. Admission-барьер (review #95, job `admission`)
в лист решения §2 также не входит. Поэтому согласие с §2 не является подтверждением ни
SAN, ни барьера. Значение SAN не угадывается (runbook §3 п. 1).

## Следствие для подготовки (что НЕ завершено)

Из-за нехватки входов не выполнено (runbook `P8C_REVIEW_97_RUNBOOK.md` §3 п. 1–3):

- `PINNED_TOOLS_SHA` остаётся протухшим `32a38ea1223ab8b0e10913a3c32c95d62c2661c6`
  (без `workflow-blob`) — финализация точного tools SHA блокируется п. 1 (подтверждение
  identity/SAN предшествует отдельному tools-коммиту).
- `WORKFLOW_IDENTITY` остаётся плейсхолдером; финальные байты workflow не зафиксированы.
- Отдельный tools-коммит с подтверждённой identity и кандидат YAML с точными
  `PINNED_TOOLS_SHA` + `WORKFLOW_IDENTITY` НЕ создавались.

## Границы соблюдены

Workflow не публиковался и не активировался; dispatch не выполнялся; build/push/sign/attest
не выполнялись; действующие pins/секреты/`images.lock`/`versions.lock` не менялись.
Старый workflow из `main` для обхода review не использовался. Секреты и токены в отчёт
не включены. Digest/provenance остаются `NOT_VERIFIED`.

```text
OWNER_SAN_CONFIRMATION = MISSING (владелец)
ISSUER_IDENTITY_TRUST_EVIDENCE = MISSING (владелец)
EXCLUSIVE_ADMISSION_BARRIER = MISSING (владелец)
TOOLS_SHA_FINALIZED = NO (блокируется SAN)
WORKFLOW_BYTES_FINALIZED = NO (блокируется SAN)
WORKFLOW_PUBLICATION / DISPATCH / BUILD / PUSH / SIGN / ATTEST = NOT_AUTHORIZED
LOCK_UPDATE = NOT_PERFORMED (apply_lock = false)
APPLICATION_DIGEST / SLSA_PROVENANCE = NOT_VERIFIED
```

## Критерии проверки (архитектор)

1. Каждый отсутствующий факт назван с ответственным и требуемым ответом (3 позиции).
2. Показано, что согласие с §2 не подменяет значение SAN (SAN вне §2, плейсхолдер).
3. `PINNED_TOOLS_SHA` не финализирован и не выдаётся за готовый; `WORKFLOW_IDENTITY` —
   плейсхолдер; нет заявления о готовых байтах workflow.
4. Никаких build/push/sign/attest/lock-update/publish/dispatch инженером не выполнялось.
5. Отчёт не содержит секретов/токенов.
