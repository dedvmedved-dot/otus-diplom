# Решение архитектора по #148: STOP, выпуск B — NOT_READY

Принят вывод [PR #147](https://git.aiopslab.online/aiopslab/otus-diplom/pulls/147), проверенный SHA `8d2b844579b3a236d6bccf9e8e2efe1c007eb811`. Обновлять нужно исполняющий runner, не workflow и не серверный jobparser.

[Выписка оператора из журнала task 224](https://git.aiopslab.online/aiopslab/otus-diplom/issues/144#issuecomment-12142) подтверждает: именно `otus-diplom(version:v6.1.0)` принял job `diagnostic` в run 71. На SHA `c2194b161fe7e5e5218bd737c335faa63c41db0d` ключ `enable-openid-connect: true` стоит на уровне workflow (`.forgejo/workflows/oidc-diagnostic.yml:33`), без переопределения у job. В jobparser v12.10.2 это означает наследование. В Forgejo v15.0.11 `services/actions/task.go:162–187` при этом флаге заполняет поля контекста задачи; исключение для fork-PR к `workflow_dispatch` не относится. Содержимое контекста живой задачи не проверялось.

Независимая сверка тегов [forgejo/runner](https://code.forgejo.org/forgejo/runner):

| Тег | SHA исходников | Результат |
|---|---|---|
| v6.1.0 | `94f94a56d48ea3da3479a3b9e90e643e23ebb148` | `git grep -inE 'ACTIONS_ID_TOKEN_REQUEST_|forgejo_actions_id_token_request_' v6.1.0` по всему дереву: 0 совпадений, код 1. |
| v12.4.0 | `a4f4474fed53d9a687e4363116b07b33c1f6f66f` | В `internal/app/run/runner.go` инъекции нет. Чтение env в JS не является инъекцией. |
| v12.5.0 | `b35a1e49f49409cb8fb6bf79a4a0ee9613fc6f14` | Первый релиз с присваиванием обоих полей из `taskContext` в `runEnvs`: `internal/app/run/runner.go:315–316`. |
| v12.10.2 | `bbac773579d5f93ffe0c266a114d7312daab146a` | Там же, строки 313–314: `ACTIONS_ID_TOKEN_REQUEST_TOKEN` и `ACTIONS_ID_TOKEN_REQUEST_URL`. |

Оператору: обновить runner `otus-diplom` с v6.1.0 до проверенной v12.10.2. До допуска подтвердить версию именно работающего сервиса и его готовность принимать задачи, без запуска workflow. Не подставлять токен через env или secrets.

Допуск #141 исчерпан. Только после обновления и отдельного допуска владельца возможен один новый диагностический запуск на согласованном SHA; фиксировать наличие обеих переменных и результат проверки `iss`/`aud`/`sub`, не публикуя URL, токены или JWT. Пока известен только отказ run 71 по отсутствию URL; успех выдачи после обновления не доказан. Run 71 не повторять; PR #140 не сливать без нового решения.
