# SECURITY-INCIDENT-001 — Утечка root SSH-пароля в Git history

**Дата:** 2026-08-11
**Обнаружил:** GitHub Connector (Главный Архитектор)
**Серьёзность:** HIGH
**Статус:** MITIGATED

---

## Описание

Commit `28e4d66f5ff10f2fb958fc65144c4d942af4efc3` (TASK-007) содержал файл
`inventory/hosts.yaml` с root SSH-паролем узлов ПАК в открытом виде:

```yaml
ansible_ssh_pass: "[REDACTED — ROTATED AND INVALIDATED]"
```

Репозиторий публичный (`github.com/dedvmedved-dot/otus-diplom`).

---

## Хронология

| Время | Событие |
| --- | --- |
| TASK-007 | Пароль добавлен в `hosts.yaml` (commit 28e4d66) |
| TASK-007 | Пароль удалён из HEAD (commit 5d76991) |
| Архитектор | Обнаружен через Connector audit |
| TASK-007 | Пароль сменён на node-01, node-02 |
| TASK-007 | Старый пароль инвалидирован |

---

## Меры

1. ✅ Root-пароль сменён на node-01 и node-02
2. ✅ Старый пароль (`!QAZxsw2123`) больше не работает
3. ✅ Новый пароль хранится в `/etc/hermes/pak_root_pass.txt` (600), не в Git
4. ✅ `StrictHostKeyChecking=no` заменён на `yes`
5. ✅ SSH host keys верифицированы
6. ⏳ Историческая очистка Git (до Final Acceptance)
7. ⏳ node-03: смена пароля сразу после возврата из ремонта

---

## Дальнейшие действия

- Переписать Git history для удаления секрета (отдельная операция после P9)
- Никогда не помещать пароли/ключи в inventory YAML
- Использовать `--ask-pass` или `ansible-vault`
