# Механизм взаимодействия агентов OTUS

Версионируемая копия механизма группы агентов OTUS (архитектор / инженер) на узле 5.187.1.37.
Без секретов — только поллеры, конфиги-шаблоны, systemd-юниты. Токены живут на хосте.

## Состав группы

| Роль | OS-пользователь | Forgejo assignee | Модель | Каталог |
|---|---|---|---|---|
| Архитектор | `hermes-5.187.1.37-a-arch` | `hermes-5.187.1.37-a-arch` | gpt-6.2-astra (openai-codex) | `arch/` |
| Инженер | `root` | `hermes-5.187.1.37-engineer` | deepseek-v4-pro | `engineer/` |

Репозиторий: `aiopslab/otus-diplom`. Хост: 5.187.1.37 (SSH `-p2222 root`).

## Поток

```
владелец → issue (assignee архитектор)
архитектор → issue (assignee инженер)       (наряд/декомпозиция)
инженер → PR/реализация → закрывает + review-issue архитектору
архитектор → APPROVE/REQUEST_CHANGES → владельцу (merge/Word-gate)
```

Юниты: `otus-poller.timer` (60 с) у обоих; gateway `otus-arch-gateway.service` (архитектор) и
`hermes-gateway.service` (инженер).

## Файлы агента

`forgejo-task-poll.py`, `agent-task.sh`, `poll.env.template` (без токена), gateway + poller-юниты,
`PROJECT_CONTEXT.md` (у архитектора).

## Развёртывание с нуля

Полный рецепт идентичен `ops/agents/README.md` репозитория `aither-project`. Секреты — на хосте.
