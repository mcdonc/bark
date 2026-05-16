{ pkgs, config, lib, ... }: {
  languages.dart = {
    enable = true;
    package = pkgs.flutter;
  };
  languages.python = {
    enable = true;
    venv.enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
    directory = "./backend";
  };

  packages = with pkgs; [
    docker-client
    nginx
  ];

  tasks = {
    "bark:flutter-build" = {
      exec = "flutterbuildweb";
      showOutput = true;
      execIfModified = [
        "frontend/lib"
        "frontend/web"
        "frontend/pubspec.yaml"
        "frontend/pubspec.lock"
        "${config.env.BARK_PLUGINS_DIR}/**/*.dart"
        "${config.env.BARK_PLUGINS_DIR}/plugins.lock"
      ];
    };
    "bark:docker-build" = {
      exec = "dockerbuild";
      showOutput = true;
      execIfModified = [
        "docker/Dockerfile"
        "docker/entrypoint.sh"
        "${config.env.BARK_PLUGINS_DIR}/**/*.ts"
        "${config.env.BARK_PLUGINS_DIR}/**/tools/**"
        "${config.env.BARK_PLUGINS_DIR}/plugins.lock"
      ];
    };
  };

  processes = {
    backend = {
      exec = ''
        cd $DEVENV_ROOT/backend && exec uvicorn backend.main:app --host 0.0.0.0 --port $BARK_PORT
      '';
      after = [
        "bark:flutter-build"
        "bark:docker-build"
      ];
    };
    nginx = {
      exec = ''
        mkdir -p $DEVENV_STATE/nginx
        cat > $DEVENV_STATE/nginx/nginx.conf << 'NGINX'
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

          map $http_upgrade $connection_upgrade {
            default upgrade;
            "" close;
          }

          client_max_body_size 500m;

          server {
            listen ${toString config.env.BARK_NGINX_PORT};

            location /bark/ {
              proxy_pass http://127.0.0.1:${config.env.BARK_PORT}/;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $scheme;
              proxy_http_version 1.1;
              proxy_set_header Upgrade $http_upgrade;
              proxy_set_header Connection $connection_upgrade;
              sub_filter '<base href="/">' '<base href="/bark/">';
              sub_filter_once on;
            }

            location / {
              proxy_pass http://127.0.0.1:${toString config.env.BARK_SOLIPLEX_PORT}/;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $scheme;
              proxy_http_version 1.1;
              proxy_set_header Upgrade $http_upgrade;
              proxy_set_header Connection $connection_upgrade;
            }
          }
        }
        NGINX
        echo "nginx listening on port $BARK_NGINX_PORT" >&2
        exec nginx -e stderr -c $DEVENV_STATE/nginx/nginx.conf
      '';
      after = [
        "bark:flutter-build"
        "bark:docker-build"
      ];
    };
  };

  env.SOURCE_DATE_EPOCH = "";
  env.UV_PYTHON = config.devenv.state + "/venv/bin/python";
  # Port defaults use mkOverride 1500 (lower priority than mkDefault/1000).
  # dotenv.enable loads .env values as mkDefault, so .env entries override these.
  # devenv.local.nix with lib.mkForce overrides everything.
  # Priority: devenv.local.nix (mkForce/50) > .env (mkDefault/1000) > these defaults (1500)
  env.BARK_PORT = lib.mkOverride 1500 "8997";
  env.BARK_NGINX_PORT = lib.mkOverride 1500 "8995";
  env.BARK_SOLIPLEX_PORT = lib.mkOverride 1500 "8555";
  env.BARK_DATA_DIR = lib.mkOverride 1500 (builtins.getEnv "HOME" + "/.bark/data");
  env.BARK_PLUGINS_DIR = lib.mkOverride 1500 (builtins.getEnv "HOME" + "/.bark/plugins");
  dotenv.enable = true;

  scripts.flutterbuildweb.exec = ''
    cd $DEVENV_ROOT
    # Auto-fetch plugins on first run
    if [ -f $BARK_PLUGINS_DIR/plugins.yaml ] && [ ! -f $BARK_PLUGINS_DIR/plugins.lock ]; then
      echo "No plugins.lock found, running update-plugins..."
      python3 scripts/update_plugins.py
    fi
    python3 scripts/import_plugins.py
    cd frontend && flutter --disable-analytics && flutter pub get && flutter build web --base-href=/bark/ --no-wasm-dry-run
    rm -f build/web/flutter_service_worker.js
  '';

  scripts.dockerbuild.exec = ''
    cd $DEVENV_ROOT
    # Auto-fetch plugins on first run
    if [ -f $BARK_PLUGINS_DIR/plugins.yaml ] && [ ! -f $BARK_PLUGINS_DIR/plugins.lock ]; then
      echo "No plugins.lock found, running update-plugins..."
      python3 scripts/update_plugins.py
    fi
    # Collect plugin files into docker build context
    rm -rf docker/extensions docker/tools
    mkdir -p docker/extensions docker/tools
    for d in $BARK_PLUGINS_DIR/*/; do
      [ -d "$d" ] || continue
      name=$(basename "$d")
      # TypeScript extensions
      [ -f "$d/extension.ts" ] && cp "$d/extension.ts" "docker/extensions/$name.ts"
      # Server-side tools (any files in tools/ subdir)
      [ -d "$d/tools" ] && cp -r "$d/tools/"* docker/tools/ 2>/dev/null
    done
    # Remove old containers before rebuilding so they get recreated from the new image
    docker ps -a --filter ancestor=bark-pi -q | xargs -r docker rm -f
    docker build --platform linux/amd64 --build-arg BARK_UID=$(id -u) --build-arg BARK_GID=$(id -g) -t bark-pi docker/
  '';

  scripts.rebuild.exec = ''
    echo "Rebuilding Bark..."
    echo "==> Docker image"
    dockerbuild
    echo "==> Flutter web"
    flutterbuildweb
    echo "==> Done"
  '';

  scripts.update-plugins.exec = ''
    cd $DEVENV_ROOT
    python3 scripts/update_plugins.py "$@"
  '';

  enterShell = ''
    mkdir -p "$BARK_DATA_DIR"
    echo "Bark dev environment ready"
    echo "Run 'rebuild' to rebuild all sofware."
    echo "Run 'devenv processes up' to start backend + frontend"
  '';
}
