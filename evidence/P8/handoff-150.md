# Решение архитектора по #150

[Оператор подтвердил](https://git.aiopslab.online/aiopslab/otus-diplom/issues/148#issuecomment-12351) версию работающего runner `otus-diplom` v12.10.2 без dispatch. Затем [владелец отдельно разрешил один новый запуск](https://git.aiopslab.online/aiopslab/otus-diplom/issues/148#issuecomment-12364); повторно запрашивать допуск не требуется.

Единственный исполнитель — назначенный инженер. Непосредственно перед запуском проверить, что допуск ещё не использован и удалённый `refs/heads/engineer/139-oidc-enable-openid` указывает на `c2194b161fe7e5e5218bd737c335faa63c41db0d`. При расхождении или неопределённости — STOP. Отправить ровно один `workflow_dispatch` для `oidc-diagnostic.yml`. Не повторять запрос даже при тайм-ауте; rerun запрещён.

Вернуть архитектору ссылку, ID, ref, фактический SHA и статус run. Указать, переданы ли шагу `ACTIONS_ID_TOKEN_REQUEST_URL` и `ACTIONS_ID_TOKEN_REQUEST_TOKEN`, без их значений. При успехе зафиксировать только `iss`, `aud`, `sub`; при неудаче — наблюдаемую причину или отсутствие данных. Не публиковать JWT, заголовки или полный payload.

Выпуск B остаётся NOT_READY. Допуск не разрешает build/push/sign/attest/lock/публикацию, merge #140 или изменения workflow и сервера.
