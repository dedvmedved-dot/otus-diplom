# Решение архитектора по #153 — 2026-11-28

Выдачу OIDC id-token диагностическому шагу принимаю. Фактические значения claims по логу пока не подтверждены. Выпуск B — NOT_READY.

Forgejo API показывает `failure` для [run 71](https://git.aiopslab.online/aiopslab/otus-diplom/actions/runs/3) и `success` для [run 72](https://git.aiopslab.online/aiopslab/otus-diplom/actions/runs/4). В обоих случаях `workflow_id=oidc-diagnostic.yml`, `commit_sha=c2194b161fe7e5e5218bd737c335faa63c41db0d`. Это согласуется с [обновлением работающего runner с v6.1.0 до v12.10.2](https://git.aiopslab.online/aiopslab/otus-diplom/issues/148#issuecomment-12351). [Допуск](https://git.aiopslab.online/aiopslab/otus-diplom/issues/148#issuecomment-12364) использован; не повторять.

В [workflow на проверенном SHA](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/c2194b161fe7e5e5218bd737c335faa63c41db0d/.forgejo/workflows/oidc-diagnostic.yml) нет пропуска второго шага или игнорирования его ошибки. Успех означает, что обе переменные запроса непусты, endpoint ответил HTTP 200 и шаг декодировал `iss`, `aud`, `sub` из полученного токена. Шаг не сравнивает значения и не проверяет подпись JWT. Это свидетельство выдачи, а не проверка доверия или идентичности выпуска.

Первичный лог архитектор не получил (HTTP 404 с API-учётными данными). `aud=sigstore` и `sub=repo:aiopslab/otus-diplom:ref:refs/heads/engineer/139-oidc-enable-openid` остаются прогнозом. Issuer из discovery также не заменяет `iss` данного токена.

Оператору: из существующего run 72 приложить в #153 только обе строки `ENV_PRESENT` (имена без значений), `OIDC_ISS`, `OIDC_AUD`, `OIDC_SUB`. Не прикладывать весь лог, JWT, payload, заголовки или значения env. До сверки оставить критерий 1 открытым. Новый запуск, merge #140 и действия по выпуску B не разрешены.
