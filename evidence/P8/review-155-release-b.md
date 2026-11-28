# Решение #155: диагностика OIDC принята; выпуск B не разрешён

По [выписке владельца из task 225](https://git.aiopslab.online/aiopslab/otus-diplom/issues/153#issuecomment-12397) критерий 1 ревью #153 закрыт. В [run 72](https://git.aiopslab.online/aiopslab/otus-diplom/actions/runs/4) на SHA `c2194b161fe7e5e5218bd737c335faa63c41db0d` runner v12.10.2 передал обе переменные запроса, endpoint вернул HTTP 200. Наблюдаемые claims:

- `iss`: `https://git.aiopslab.online/api/actions`
- `aud`: `sigstore`
- `sub`: `repo:aiopslab/otus-diplom:ref:refs/heads/engineer/139-oidc-enable-openid`

Первый B — **NOT_READY_FOR_DISPATCH**. Это subject диагностической ветки, не подтверждение SAN сертификата выпуска, доверия подписывающей стороны или admission-барьера. Диагностический допуск исчерпан.

[Наряд #156](https://git.aiopslab.online/aiopslab/otus-diplom/issues/156) назначен `hermes-5.187.1.37-engineer`: сверить имеющиеся доказательства для release workflow и вернуть архитектору в #155 пакет для решения владельца либо конкретный блокер с исполнителем. Новые запуски, merge #140, изменение policy и операции выпуска не разрешены.
