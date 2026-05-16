#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${DEVENV_ROOT:-$SCRIPT_DIR/..}"

# Auto-fetch plugins on first run
if [ -f "$BARK_PLUGINS_DIR/plugins.yaml" ] && [ ! -f "$BARK_PLUGINS_DIR/plugins.lock" ]; then
  echo "No plugins.lock found, running update-plugins..."
  python3 scripts/update_plugins.py
fi

# Collect plugin files into docker build context
rm -rf docker/extensions docker/tools
mkdir -p docker/extensions docker/tools
for d in "$BARK_PLUGINS_DIR"/*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  # TypeScript extensions
  [ -f "$d/extension.ts" ] && cp "$d/extension.ts" "docker/extensions/$name.ts"
  # Server-side tools (any files in tools/ subdir)
  [ -d "$d/tools" ] && cp -r "$d/tools/"* docker/tools/ 2>/dev/null
done

# Remove old containers before rebuilding so they get recreated from the new image
docker ps -a --filter "label=bark.instance=${BARK_INSTANCE_ID}" -q | xargs -r docker rm -f
docker build --platform linux/amd64 --build-arg BARK_UID="$(id -u)" --build-arg BARK_GID="$(id -g)" -t "${BARK_IMAGE_NAME}" docker/
