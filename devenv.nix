{ pkgs, ... }: {
  languages.dart = {
    enable = true;
    package = pkgs.flutter;
  };
  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
    directory = "./backend";
  };

  packages = with pkgs; [
    docker-client
  ];

  processes = {
    backend.exec = ''
      cd $DEVENV_ROOT
      # Build frontend if not already built
      if [ ! -d frontend/build/web ]; then
        echo "Building Flutter app..."
        flutterbuildweb
      fi
      # Build Pi agent Docker image if not already built or Dockerfile changed
      if ! docker image inspect bark-pi >/dev/null 2>&1 || \
         [ docker/Dockerfile -nt "$(docker image inspect bark-pi --format='{{.Created}}' 2>/dev/null || echo '0')" ]; then
        echo "Building bark-pi Docker image..."
        dockerbuild
      fi
      cd backend && uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8997
    '';
  };

  dotenv.enable = true;

  scripts.flutterbuildweb.exec = ''
    cd $DEVENV_ROOT
    cd frontend && flutter pub get && flutter build web
    rm -f build/web/flutter_service_worker.js
  '';

  scripts.dockerbuild.exec = ''
    cd $DEVENV_ROOT
    docker build --platform linux/amd64 -t bark-pi docker/
  '';

  scripts.rebuild.exec = ''
    echo "Rebuilding Bark..."
    echo "==> Docker image"
    dockerbuild
    echo "==> Flutter web"
    flutterbuildweb
    echo "==> Done"
  '';

  enterShell = ''
    export BARK_DATA_DIR="''${DEVENV_STATE}/.bark"
    mkdir -p "$BARK_DATA_DIR"
    echo "Bark dev environment ready"
    echo "Run 'rebuild' to rebuild all sofware."
    echo "Run 'devenv processes up' to start backend + frontend"
  '';
}
