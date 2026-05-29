#!/usr/bin/env python3
"""Write Pi agent models.json and merge settings.json.

Run standalone to update Pi config without launching Pi. Merges image
packages with user-installed packages, preserving user additions and
removing packages dropped from the image.
"""

import json
import os
from pathlib import Path

IMAGE_DIR = Path("/opt/klangk/pi-agent")
AGENT_DIR = Path.home() / ".pi" / "agent"
SIDECAR = AGENT_DIR / ".image-packages"


def _pkg_name(p):
    """Extract package name from a string or dict entry."""
    return p["name"] if isinstance(p, dict) else str(p)


def write_models_json():
    """Write models.json with proxy URL (no real API key)."""
    proxy_url = os.environ.get("KLANGK_LLM_PROXY_URL", "")
    model = os.environ.get("KLANGK_LLM_MODEL", "")
    models = {
        "providers": {
            "llm-proxy": {
                "baseUrl": proxy_url,
                "api": "openai-completions",
                "apiKey": "proxy",
                "models": [{"id": model}],
            }
        }
    }
    AGENT_DIR.mkdir(parents=True, exist_ok=True)
    (AGENT_DIR / "models.json").write_text(json.dumps(models, indent=2))


def merge_settings():
    """Merge image settings.json with user settings, preserving user packages.

    Image-managed package names are tracked in a sidecar file. On each start:
    - Packages in the old sidecar but not in the current image are removed
    - Current image packages are added/updated
    - User-installed packages (never in any sidecar) are preserved
    """
    image_settings = json.loads((IMAGE_DIR / "settings.json").read_text())
    image_pkgs = image_settings.get("packages", [])
    image_pkg_names = {_pkg_name(p) for p in image_pkgs}

    # Read previous sidecar (what the image managed last time)
    old_image_names = set()
    if SIDECAR.exists():
        old_image_names = {
            n.strip() for n in SIDECAR.read_text().splitlines() if n.strip()
        }

    user_settings_path = AGENT_DIR / "settings.json"
    if user_settings_path.exists():
        settings = json.loads(user_settings_path.read_text())
        existing_pkgs = settings.get("packages", [])

        # Remove packages that were image-managed but are no longer in image
        dropped = old_image_names - image_pkg_names
        existing_pkgs = [p for p in existing_pkgs if _pkg_name(p) not in dropped]

        # Remove existing image packages (will be re-added from current image)
        existing_pkgs = [
            p for p in existing_pkgs if _pkg_name(p) not in image_pkg_names
        ]

        # Add current image packages
        settings["packages"] = existing_pkgs + image_pkgs
    else:
        settings = image_settings

    # Set LLM config
    model = os.environ.get("KLANGK_LLM_MODEL", "")
    settings["defaultProvider"] = "llm-proxy"
    settings["defaultModel"] = model

    user_settings_path.write_text(json.dumps(settings, indent=2))

    # Write sidecar
    SIDECAR.write_text("\n".join(sorted(image_pkg_names)) + "\n")


if __name__ == "__main__":
    write_models_json()
    merge_settings()
    print("Pi config updated (models.json + settings.json)")
