# #114 — приёмка отчёта о подготовке первого B

Отчёт [PR #113](https://git.aiopslab.online/aiopslab/otus-diplom/pulls/113) на `3408f58bd0c6f0be665ab2386e779dd623b9d52f` принят. Принят вывод о нехватке данных, а не готовность к dispatch.

- В `P8C_PREP_B_112.md` для каждого из трёх входов названы владелец и требуемый ответ: точный SAN с привязкой к workflow, независимое свидетельство доверия issuer/identity, эксклюзивная выдача задания runner после gate.
- [Решение владельца](https://git.aiopslab.online/aiopslab/otus-diplom/issues/68#issuecomment-6826) разрешает B с `apply_lock=false`. Согласие с §2 не удостоверяет SAN: в §1 листа решения на `09beada8` identity явно не проверена.
- `WORKFLOW_IDENTITY` остаётся плейсхолдером, `PINNED_TOOLS_SHA` не финализирован; утверждённого workflow по байтам нет.
- В diff #113 только инженерный отчёт. Секретов и токенов в его тексте не обнаружено. По отчёту publish/dispatch/build/push/sign/attest и запись lock не выполнялись; diff не является аудитом внешнего registry или runner. Digest/provenance: `NOT_VERIFIED`.

[Единый запрос владельцу в #111](https://git.aiopslab.online/aiopslab/otus-diplom/issues/111#issuecomment-7681). До трёх подтверждений — `BLOCKED / NOT_READY_FOR_DISPATCH`. После проверки ответов — отдельный наряд инженеру на точный tools SHA и финальные байты workflow, затем отдельное review публикации. Повторного выбора A/B/C не требуется.
