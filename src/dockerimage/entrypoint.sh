#!/bin/sh
# bark user is created at build time with the host UID/GID.
# This entrypoint runs as root, sets up Pi config, then drops to bark.

# Set up Pi agent config in bark's home (copied from build-time /opt/bark).
# /home/bark is a persistent bind mount, so clean the agent dir first to
# avoid stale files from previous container starts.
PI_AGENT_DIR="/home/bark/.pi/agent"
rm -rf "$PI_AGENT_DIR"
mkdir -p "$PI_AGENT_DIR/extensions"
cp -r /opt/bark/pi-agent/extensions/* "$PI_AGENT_DIR/extensions/" 2>/dev/null

# Write models.json — no secrets here since the LLM proxy injects the
# API key on the host side. The container only sees the proxy URL.
cat >"$PI_AGENT_DIR/models.json" <<EOF
{
  "providers": {
    "llm-proxy": {
      "baseUrl": "$LLM_BASE_URL",
      "api": "openai-completions",
      "apiKey": "proxy",
      "models": [
        { "id": "$LLM_MODEL" }
      ]
    }
  }
}
EOF

cat >"$PI_AGENT_DIR/settings.json" <<EOF
{
  "defaultProvider": "llm-proxy",
  "defaultModel": "$LLM_MODEL"
}
EOF

# Fix ownership: bark's home + workspace directory
# /home/bark/.pi/sessions persists on the host via the /home/bark bind mount
chown -R bark:bark /home/bark
chown bark:bark /work

# Allow bark to use git in /work
su bark -c "git config --global --add safe.directory /work" 2>/dev/null

# Build system prompt file from static template + registered extension tools
SYSTEM_PROMPT_FILE="$PI_AGENT_DIR/system-prompt.md"
cp /opt/bark/system-prompt.md "$SYSTEM_PROMPT_FILE"

if [ -d "$PI_AGENT_DIR/extensions" ] && [ "$(ls "$PI_AGENT_DIR/extensions"/*.ts 2>/dev/null)" ]; then
  echo "" >>"$SYSTEM_PROMPT_FILE"
  echo "Registered extension tools (use these instead of bash when appropriate):" >>"$SYSTEM_PROMPT_FILE"
  for ext in "$PI_AGENT_DIR/extensions"/*.ts; do
    name=$(grep -E '^\s+name: "' "$ext" | head -1 | sed 's/.*name: "//;s/".*//')
    desc=$(grep -E '^\s+description: "' "$ext" | head -1 | sed 's/.*description: "//;s/".*//')
    if [ -n "$name" ] && [ -n "$desc" ]; then
      echo "- \`$name\`: $desc" >>"$SYSTEM_PROMPT_FILE"
    fi
  done
fi

# Build Pi command line
PI_CMD="exec pi --mode rpc --no-context-files --append-system-prompt $SYSTEM_PROMPT_FILE --session-dir /home/bark/.pi/sessions"
if [ -n "$BARK_RESUME_SESSION" ]; then
  PI_CMD="$PI_CMD --session $BARK_RESUME_SESSION"
fi

# Drop to bark user and run Pi.
# shellcheck disable=SC2086
exec env -u BARK_RESUME_SESSION \
  su bark -c "PI_CODING_AGENT_DIR=$PI_AGENT_DIR $PI_CMD"
