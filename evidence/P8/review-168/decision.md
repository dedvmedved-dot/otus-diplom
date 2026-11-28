# Решение архитектора по #168: требуются изменения

Объект: [PR #167](https://git.aiopslab.online/aiopslab/otus-diplom/pulls/167), head `b8da2b096f8829359f3da7916ef1c4375261116a`, base `53dcd7fc91e53979df687f43578bd75e0ff9c9cc`.

Принято: шаблон и опубликованный workflow имеют один git blob `46f8bdc9956655f065a54f3e09540357034cc7f1`. Ручной trigger, admission → test → preflight → release, OIDC только у release. Source `4c09d6b4a85e2d021516244988f48b92eade7acf` разрешается; tools `3395d0cca3475efc1c4df910c1188bc5fe9db2d5` содержит тот же gate, что и head (blob `ab1fda0d6ca033cecc93126e8f6a49cc08aea2c7`). В шаблоне и gate закреплён `repo:aiopslab/otus-diplom:ref:refs/heads/main`, сравнение точное. Все три команды проверки используют этот SAN и issuer `https://git.aiopslab.online/api/actions`.

Блокируют приёмку:

1. `forgejo_lock_gate.py:912–914,991,1457–1469`: ожидаемый audience допускает переопределение через bindings/CLI. Stage 4 сравнивает два значения между собой, не требуя независимо литерал `sigstore`. Нужен отказ также при совпадающих неверных значениях.
2. Workflow:604–609,630–631,678–680: `--oidc-client-id` указан у sign, но не у двух attest; `certificate_audience` берётся из env политики, а не из подтверждённого токена/результата проверки. Нельзя выдавать его за наблюдение. Нужна проверяемая привязка фактического token audience для всех трёх операций; токены не логировать и не сохранять.
3. Workflow:458–463,598–653: `oidc_trust_confirmed=false` блокирует release, но `true` не проверяет наличие, подлинность и применение частной конфигурации/корней. Sign/attest/verify не привязаны здесь к проверенной частной конфигурации. До отдельного развёртывания приемлем безусловный отказ до push при отсутствии необходимых материалов; отсутствие публичного fallback должно обеспечиваться кодом, не комментарием.

Независимый прогон: 177/177 тестов OK под системным Python с PyYAML, syntax VERIFIED (4 jobs, 97 expressions), CLI flags 5/5 OK. Последние проверяют разбор флагов, не выпуск токена или сертификата. Операционный admission-барьер не выполнен; merge и dispatch не разрешены и остаются отдельными решениями. В рамках review не выполнялись dispatch/rerun, push образа, sign/attest, обновление release-lock.
