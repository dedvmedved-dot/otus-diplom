# Решение по OIDC-пилоту #130

Срез Forgejo API: 26 ноября 2026, 19:02 UTC. Наряд #129 исполнен в части единственного dispatch, но OIDC identity не установлена.

В истории репозитория один [run](https://git.aiopslab.online/aiopslab/otus-diplom/actions/runs/1): ID 69, номер 1 (`index_in_repo`), событие `workflow_dispatch`, инициатор `hermes-5.187.1.37-engineer`. Workflow `.forgejo/workflows/oidc-diagnostic.yml`, ref `refs/heads/engineer/126-oidc-pilot` и commit `95f6cb271b2da4053b157c81317c46641ac556d0` совпадают с [разрешением владельца](https://git.aiopslab.online/aiopslab/otus-diplom/issues/127#issuecomment-10410). На этом SHA единственный job `diagnostic` требует label `otus-diplom`.

Run ожидает: `waiting`, `need_approval=false`, `started=1970-01-01T00:00:00Z`, число tasks — 0. Признаков исполнения или повторного запуска нет. API не показывает счётчик попыток; инженер отдельно указал, что rerun не выполнялся. Запрос списка runners от архитектора вернул HTTP 403. Это ограничение видимости, не доказательство отсутствия регистрации или offline.

- `iss`, `aud`, `sub`: **BLOCKED**, фактических значений нет.
- Выпуск B: **NOT_READY_FOR_DISPATCH**; digest/provenance: **NOT_VERIFIED**.
- [Владельцу и через него оператору CA](https://git.aiopslab.online/aiopslab/otus-diplom/issues/111#issuecomment-10484): проверить runner без изменения состояния; подтвердить выпускной SAN, привязку к workflow/ref, issuer/audience, политику CA и корни доверия. Даже успешный диагностический `sub` сам по себе не устанавливает SAN выпуска. Отдельный барьер допуска B остаётся обязательным.
- Не давать повторный dispatch/rerun: разрешение исчерпано созданием run 69. При восстановлении runner существующая очередь может начать исполняться; сначала сверить статус именно 69. Для нового пилота нужны отдельное разрешение владельца и новый наряд. До ответа владельца инженерных действий не требуется.
