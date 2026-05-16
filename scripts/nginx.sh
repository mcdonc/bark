#!/usr/bin/env bash
set -euo pipefail

NGINX_STATE="${DEVENV_STATE:?DEVENV_STATE must be set}/nginx"
mkdir -p "$NGINX_STATE"

cat > "$NGINX_STATE/nginx.conf" << NGINX
daemon off;
pid /tmp/nginx.pid;
error_log stderr;
events { worker_connections 64; }
http {
  access_log /dev/stdout;
  client_body_temp_path /tmp/nginx_client_body;
  proxy_temp_path /tmp/nginx_proxy;
  fastcgi_temp_path /tmp/nginx_fastcgi;
  uwsgi_temp_path /tmp/nginx_uwsgi;
  scgi_temp_path /tmp/nginx_scgi;

  map \$http_upgrade \$connection_upgrade {
    default upgrade;
    "" close;
  }

  client_max_body_size 500m;

  server {
    listen ${BARK_NGINX_PORT};

    location /bark/ {
      proxy_pass http://127.0.0.1:${BARK_PORT}/;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
      proxy_http_version 1.1;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection \$connection_upgrade;
      sub_filter '<base href="/">' '<base href="/bark/">';
      sub_filter_once on;
    }

    location / {
      proxy_pass http://127.0.0.1:${BARK_SOLIPLEX_PORT}/;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
      proxy_http_version 1.1;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection \$connection_upgrade;
    }
  }
}
NGINX

echo "nginx listening on port $BARK_NGINX_PORT" >&2
exec nginx -e stderr -c "$NGINX_STATE/nginx.conf"
