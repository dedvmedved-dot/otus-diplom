#!/bin/bash
# JMS agent task wrapper: run the agent for a Forgejo issue, then notify Telegram.
# Usage: agent-task.sh ROLE ISSUE_NUM TITLE
ROLE="$1"; ISSUE="$2"; TITLE="$3"
HERMES="$HOME/.local/bin/hermes"
PROMPT_FILE="$HOME/.hermes/task-prompt-${ISSUE}.txt"

if [ ! -f "$PROMPT_FILE" ]; then
    echo "prompt file not found: $PROMPT_FILE" >&2
    exit 3
fi

"$HERMES" send -t telegram "▶️ ${ROLE} приступил к #${ISSUE}: ${TITLE}" 2>&1 || true

"$HERMES" chat -q "$(cat "$PROMPT_FILE")"
RC=$?

if [ "$RC" -eq 0 ]; then
    "$HERMES" send -t telegram "✅ ${ROLE} завершил #${ISSUE}: ${TITLE}. Отчёт — в комментарии issue #${ISSUE}." 2>&1 || true
else
    "$HERMES" send -t telegram "⚠️ ${ROLE}: задача #${ISSUE} (${TITLE}) завершилась с ошибкой, код ${RC}." 2>&1 || true
fi

exit "$RC"
