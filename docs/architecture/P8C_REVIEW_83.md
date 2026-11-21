# Ре-ревью #83: PR #78 принят

Head: `32a38ea1223ab8b0e10913a3c32c95d62c2661c6`; исправление: `c523eb825d726383546dc4e07b62d6bb5455fe51`; base: `aeed3b314fa0fc00626310dec8a4a9f81d3f248b`.

Блокер #82 устранён. После проверки `samefile` функция `apply_lock_pair` читает `trusted`, создаёт временный файл в `trusted.parent`, получает режим из `trusted.stat()` и передаёт `trusted` как назначение `os.replace`. Регрессия `test_replace_targets_verified_reference_not_input_alias` прошла: при входе через другое имя того же inode корневой `images.lock` получил ожидаемые байты, а байты алиаса не изменились.

Независимый прогон на head: `test_forgejo_lock_gate` — 89/89; `test_forgejo_offline_integration` — 37/37; `test_forgejo_boundary_regressions` — 19/19. `verify-pins.py --offline` на копии подготовленного кеша: 10/10 VERIFIED.

Первый полный прогон с общим `/tmp` завершился ошибкой: fake-tool E2E не смог записать принадлежащие root файлы BuildKit pid/log; также упали две стадии architect. Повтор того же `run_offline_suite.sh` с тем же кешем, системным Python и отдельным пустым каталогом, отображённым в `/tmp` через PRoot: 22/22 стадии PASS, `SUITE RESULT: PASS`, exit 0. Код и тесты между прогонами не менялись. Workflow и merge не выполнялись; реальный `images.lock` без изменений.
