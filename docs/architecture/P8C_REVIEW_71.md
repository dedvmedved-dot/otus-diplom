# #71 — повторное ревью листа решения владельца

**Лист принят для передачи владельцу.** Замечания #69 к PR #68 устранены в `09beada86000224d29678ed5c686716f53824da8`; база — `d22aa8f1170deaf09580518916ea02c7c4d8bfba`. Уточнение [в #67](https://git.aiopslab.online/aiopslab/otus-diplom/issues/67#issuecomment-1865) соответствует исправленному листу.

1. **§1, перечень путей.** Команда `git ls-tree -r --name-only d22aa8f1170deaf09580518916ea02c7c4d8bfba | LC_ALL=C sort | sha256sum` дала `e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01`. Ссылка из листа указывает на `PINNED_SOURCE_TREE_SHA256` в строке 73 шаблона `4f691ea675c6a0e0dc769ad3847dd4e705c4dc93`; значение совпадает. Изменение содержимого файла при неизменном списке путей этот хеш не выявляет.
2. **§1, OIDC.** Read-only discovery вернул issuer `https://git.aiopslab.online`. Ожидаемая certificate identity совпадает со строкой 97 шаблона, но остаётся `NOT_VERIFIED`: discovery не проверяет подпись. При первом разрешённом подписанном запуске требуется `cosign verify` с проверкой и identity, и issuer.
3. **§2, п.13.** Ответственный — Архитектор. При первом разрешённом запуске он подтверждает `github.actor`, `github.repository`, `github.ref` и `GITHUB_WORKFLOW_SHA`. Без успешной проверки переход к release прямо запрещён.
4. **Границы.** Относительно базы добавлен только `docs/architecture/P8C_OWNER_DECISION_67.md`; относительно ранее проверенного `e4f4cc69` изменён только этот лист. Изменений шаблона и lock нет, в дереве head нет `.forgejo/workflows/`. API Actions для head вернул 0 запусков. Секреты для выпуска не запрашивались, workflow и release в ходе ревью не запускались. Это не аудит действий вне Forgejo.

Дальнейших исправлений от инженера не требуется. Решение A/B/C остаётся за владельцем; по умолчанию `apply_lock=false`, а не допуск к запуску. Публикация и release не разрешены; digest/provenance — `NOT_VERIFIED`.
