#!/usr/bin/env bash
# This script simulates the Docker run command used by container_manager.py

# Using defaults based on the code for demonstration; replace with real paths if needed.
HOST_PATH="/tmp/bark-work-test"
HOME_PATH="/tmp/bark-home-test"
WORKSPACE_ID="test-workspace-123"
IMAGE_NAME="bark-pi:latest"

# Ensure bind mount directories exist
mkdir -p "$HOST_PATH"
mkdir -p "$HOME_PATH"

docker run -it --rm \
  --name "bark-test-container" \
  --label "bark.managed=true" \
  --label "bark.instance=default" \
  --label "bark.workspace-id=$WORKSPACE_ID" \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --tmpfs /run:rw,noexec,nosuid,size=16m \
  --tmpfs /var/log:rw,noexec,nosuid,size=16m \
  --mount type=bind,source="$HOST_PATH",target=/work \
  --mount type=bind,source="$HOME_PATH",target=/home/bark \
  --add-host=host.docker.internal:host-gateway \
  -p 9000:8000 -p 9001:8001 -p 9002:8002 -p 9003:8003 -p 9004:8004 \
  -e LLM_PROXY_URL=http://host.docker.internal:8995/llm-proxy \
  -e LLM_MODEL=gemma4:31b \
  -e PI_SKIP_VERSION_CHECK=1 \
  -e BARK_PORT_MAPPINGS=8000:9000,8001:9001,8002:9002,8003:9003,8004:9004 \
  -e BARK_WORKSPACE_ID="$WORKSPACE_ID" \
  -e BARK_HOSTING_HOSTNAME=localhost \
  -e BARK_HOSTING_PROTO=http \
  -e BARK_HOSTING_BASE_PATH="" \
  -i -a stdout -a stderr \
  "$IMAGE_NAME"
