#!/bin/sh
# bark user is created at build time with the host UID/GID.
# This entrypoint runs as root, sets up Pi config, then drops to bark.

# Set up Pi agent config in bark's home (copied from build-time /opt/bark)
PI_AGENT_DIR="/home/bark/.pi/agent"
mkdir -p "$PI_AGENT_DIR/extensions"
cp -r /opt/bark/pi-agent/extensions/* "$PI_AGENT_DIR/extensions/" 2>/dev/null

# Build models.json from environment variables
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-https://ollama.com/v1}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:31b}"
OLLAMA_API_KEY="${OLLAMA_API_KEY:-ollama}"

cat > "$PI_AGENT_DIR/models.json" << EOF
{
  "providers": {
    "ollama": {
      "baseUrl": "$OLLAMA_BASE_URL",
      "api": "openai-completions",
      "apiKey": "$OLLAMA_API_KEY",
      "models": [
        { "id": "$OLLAMA_MODEL" }
      ]
    }
  }
}
EOF

cat > "$PI_AGENT_DIR/settings.json" << EOF
{
  "defaultProvider": "ollama",
  "defaultModel": "$OLLAMA_MODEL"
}
EOF

# Fix ownership: bark's home + workspace directory
# /home/bark/.pi/sessions is bind-mounted from the host by container_manager
chown -R bark:bark /home/bark
chown bark:bark /workspace

# Allow bark to use git in /workspace
su bark -c "git config --global --add safe.directory /workspace" 2>/dev/null

# Build system prompt file with instructions + registered extension tools
SYSTEM_PROMPT_FILE="$PI_AGENT_DIR/system-prompt.md"
cat > "$SYSTEM_PROMPT_FILE" << 'STATIC'
You are a coding agent working in a project workspace directory.

When asked to write code:
- Always use the `write` tool to create files directly in the workspace
- Always use the `edit` tool to modify existing files
- Never ask the user to copy and paste code — write it to files yourself
- Use `bash` to run commands, install dependencies, and test code
- Use `read` to examine existing files before modifying them

When creating a project:
- Create proper directory structure
- Include any necessary configuration files (e.g., requirements.txt, package.json, Cargo.toml)
- Write all source files directly to disk
- Install dependencies using bash (pip install, npm install, cargo build, etc.)

Testing and running:
- The user does NOT have direct shell access to this system
- Always run and test code yourself using bash before telling the user it's done
- If something fails, fix it and try again
- For web apps, start the server and report which port it's running on
- Available ports for user apps: check $BARK_PORT_START to $BARK_PORT_END

Handling large files (CSV, logs, datasets, etc.):
- Do NOT read entire large files and send them to the LLM — this is extremely slow
- Prefer registered tools over bash for file inspection when an appropriate tool is available
- When using bash and the full file content is not necessary, read only portions (e.g., `head -20`, column headers) rather than the entire file
- For deeper analysis, write a Python script that processes the file locally and prints a summary
- Only read small files (< 10KB) directly with the `read` tool

Available runtimes: Python 3, Node.js/npm, Dart, Flutter, Rust/Cargo, GCC/G++ (build-essential)
STATIC

if [ -d "$PI_AGENT_DIR/extensions" ] && [ "$(ls "$PI_AGENT_DIR/extensions"/*.ts 2>/dev/null)" ]; then
  echo "" >> "$SYSTEM_PROMPT_FILE"
  echo "Registered extension tools (use these instead of bash when appropriate):" >> "$SYSTEM_PROMPT_FILE"
  for ext in "$PI_AGENT_DIR/extensions"/*.ts; do
    name=$(grep -E '^\s+name: "' "$ext" | head -1 | sed 's/.*name: "//;s/".*//')
    desc=$(grep -E '^\s+description: "' "$ext" | head -1 | sed 's/.*description: "//;s/".*//')
    if [ -n "$name" ] && [ -n "$desc" ]; then
      echo "- \`$name\`: $desc" >> "$SYSTEM_PROMPT_FILE"
    fi
  done
fi

# Drop to bark user and run Pi
# --no-context-files: don't look for AGENTS.md in workspace
# --append-system-prompt: inject instructions via system prompt instead
exec su bark -c "PI_CODING_AGENT_DIR=$PI_AGENT_DIR exec pi --mode rpc --no-context-files --append-system-prompt $SYSTEM_PROMPT_FILE --session-dir /home/bark/.pi/sessions"
