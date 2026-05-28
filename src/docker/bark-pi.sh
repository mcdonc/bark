#!/bin/sh
# Launch Pi with session resume. Intended as a workspace default command.
# Finds the most recent Pi session file and resumes it, or starts fresh.

SYSTEM_PROMPT="/home/bark/.pi/agent/system-prompt.md"
SESSION_DIR="/home/bark/.pi/sessions"

PI_ARGS="--no-context-files --session-dir $SESSION_DIR"

if [ -f "$SYSTEM_PROMPT" ]; then
  PI_ARGS="$PI_ARGS --append-system-prompt $SYSTEM_PROMPT"
fi

# Find the most recent session file to resume
LATEST=$(find "$SESSION_DIR" -name '*.jsonl' 2>/dev/null | sort | tail -1)
if [ -n "$LATEST" ]; then
  PI_ARGS="$PI_ARGS --session $LATEST"
fi

# shellcheck disable=SC2086
exec pi $PI_ARGS
