# #108 — замечания #106 к PR #102 устранены

Проверен tip `46e77bc9a31e43c333b73337bd928bc424e046b8`; его родитель `1e3fdc537d6c6802486cf621d28dc49283a34fa4` содержит изменения реализации, сам tip добавляет только evidence. Принимаю доработку #107 в пределах офлайн-проверки. Это не разрешение сливать #102 или публиковать workflow.

| Контроль | Независимый результат |
|---|---|
| `GOTOOLCHAIN=local GOPROXY=off go run .` в `cue-validation` из evidence #107 | 13/13. SHA-256 обеих копий политик совпадают с соответствующими файлами `portal/tools`. |
| `python3 spdx_gate_matrix.py` из того же evidence | 10/10. Отсутствующий `predicate` и `{}` по отдельности приняты CUE и отклонены gate. Та же граница для отсутствующих `name`, `documentNamespace`, `packages`. Пустой список `packages` отвергнут обоими слоями. Это проверка формы документа, не полная валидация SPDX. |
| `tools-pin-check --tools-dir` на временной копии gate и политик | Штатная пара: `tools_pin=true`, exit 0. После замены только содержимого SPDX-файла точной копией SLSA: `tools_pin=false`, exit 1, причина указывает на SPDX-путь. Проверка сверяет байты с SHA-256 для конкретного пути до push. |
| Четыре модуля unittest из #108 на tip | `Ran 179 tests`, `OK`. |
| `bash portal/tools/run_offline_suite.sh` на отдельном checkout source | `SOURCE_SHA=1e3fdc537d6c6802486cf621d28dc49283a34fa4`, `SUITE RESULT: PASS`, exit 0. Первый запуск без подготовленного окружения дал FAIL (в частности, нет `yaml` и pin-cache); успешный повтор — системный Python (`/usr/bin` первым в PATH), приватный `/tmp` через PRoot и локальная копия pin-cache. |

Порядок §3 сохраняется: владелец подтверждает SAN; точный tools SHA и байты workflow фиксируются до отдельного review публикации. Текущий SAN — плейсхолдер, tools pin не обновлён. Итог относится только к проверенным SHA. B/C не запускались, криптографический round trip не проверялся. Рабочие pins, lock, секреты и workflow этим review не менялись.
