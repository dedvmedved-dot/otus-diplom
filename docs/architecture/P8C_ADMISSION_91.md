# Допуск B после публикации #90

Решение #91: статическая проверка пройдена. Разрешена подготовка одного запуска B владельцем; READY для исполнения пока не подтверждён. Это не допуск C.

| Вход | Основание |
|---|---|
| `main` и workflow | API: #90 merged; Git: `main` = `e06a065337464284c4d6a27eb22936f0115ee899`; `.forgejo/workflows/p8c-portal-forgejo-release.yml` в этом дереве = blob `1805c93d3515c9262c45b99302fa1ef20581daaa`. Это разные идентификаторы. |
| Source / tools | Workflow закрепляет `4c09d6b4a85e2d021516244988f48b92eade7acf` / `32a38ea1223ab8b0e10913a3c32c95d62c2661c6`. На этих деревьях команда `inventory` вернула true; SHA-256 списка путей source: `e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01`. Тесты gate из tools: 89 OK. |
| Checkout / образ | Checkout закреплён на `11d5960a326750d5838078e36cf38b85af677262`; IMAGE совпадает с `portal/versions.lock` из source: `git.aiopslab.online/aiopslab/otus-diplom-portal`. |
| Секреты / runner | Владелец в #91 подтвердил REGISTRY_USERNAME, REGISTRY_TOKEN, OWNER_GATE, POLICY_WORKFLOW_SHA и регистрацию `otus-diplom`. API списков secrets и runners для архитектора: HTTP 403. Содержимое, права push и online-статус этим не проверены. Все три job требуют label `otus-diplom`. |
| Runtime | При проверке API Actions: 0 runs. Значение политики по заявлению владельца — указанный blob. Ни фактический `GITHUB_WORKFLOW_SHA` на этом runner, ни `github.run_id` первого B не наблюдались. |

## Наряд до dispatch

Инженеру: определить для установленной версии Forgejo/runner, когда фиксируются секреты job и как получить выданный сервером `github.run_id` **до** потребления OWNER_GATE. Предъявить воспроизводимое основание (исходник конкретной версии либо изолированная проверка без release-прав/секретов); отдельно подтвердить происхождение `GITHUB_WORKFLOW_SHA` и наличие `github.run_attempt`. Не менять release workflow, не запускать B для эксперимента. Если поддержанного порядка нет — вернуть BLOCKED и проект отдельного решения на ревью; не вычислять «следующий ID», не менять секрет наперегонки с job, не брать ID другого workflow или номер из URL без проверки семантики.

Владельцу `gitaiopslab`: после приёмки порядка привязки проверить online/label и доступ к пакету, повторно сверить pins и отдельно разрешить ровно один manual dispatch на `refs/heads/main`, `apply_lock=false`, `reviewed_digest` пуст. B может публиковать и подписывать образ; это не dry run. OWNER_GATE хранить только как secret: `mode=LIVE`, `owner=gitaiopslab`, `repository=aiopslab/otus-diplom`, `ref=refs/heads/main`, `package` = IMAGE; `source_sha`/`tools_sha` как выше, `workflow_sha` = независимый POLICY_WORKFLOW_SHA = наблюдаемое значение runtime, `run_id` строкой от того же run, `attempt=1`, фактический `run_attempt=1`, действительные `issued_at_utc` и `expiry_hours` (1–24). Только runtime preflight после test открывает release. При невозможности привязки, отсутствии или несовпадении значений — STOP, без rerun и без ослабления проверок. По результату вернуть ссылку на run, ID/attempt, статусы job, при успехе digest и доказательства подписи/аттестации; не публиковать секреты. До отдельного решения по C не менять `images.lock`.
