#!/usr/bin/env python3
"""Register Dart plugins as path dependencies in src/frontend/pubspec.yaml.

Scans $BARK_PLUGINS_DIR/*/dart/pubspec.yaml for plugins with Dart packages,
adds them as path dependencies in the frontend's pubspec.yaml (in a managed
section), and generates plugins_generated.dart with package imports.

No files are copied into the frontend source tree.
"""

import os
import re
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.environ.get("BARK_PLUGINS_DIR") or os.path.join(
    os.path.expanduser("~"), ".bark", "plugins"
)
FRONTEND_DIR = os.path.join(ROOT, "src", "frontend")
PUBSPEC = os.path.join(FRONTEND_DIR, "pubspec.yaml")
OUTPUT = os.path.join(FRONTEND_DIR, "lib", "tools", "plugins_generated.dart")

BEGIN_MARKER = "  # BEGIN BARK PLUGINS (managed by import_plugins.py)"
END_MARKER = "  # END BARK PLUGINS"


def find_plugins():
    """Scan plugins/*/dart/ for Dart packages, return metadata."""
    plugins = []
    if not os.path.isdir(PLUGINS_DIR):
        return plugins

    for name in sorted(os.listdir(PLUGINS_DIR)):
        plugin_dir = os.path.join(PLUGINS_DIR, name)
        dart_dir = os.path.join(plugin_dir, "dart")
        pubspec_file = os.path.join(dart_dir, "pubspec.yaml")
        plugin_dart = os.path.join(dart_dir, "lib", "plugin.dart")

        if not os.path.isfile(pubspec_file) or not os.path.isfile(plugin_dart):
            continue

        with open(pubspec_file) as f:
            pubspec = yaml.safe_load(f)

        package_name = pubspec.get("name", f"bark_plugin_{name}")

        with open(plugin_dart) as f:
            source = f.read()

        # Find class names extending ToolPlugin
        matches = re.findall(r"class\s+(\w+)\s+extends\s+ToolPlugin", source)
        if not matches:
            continue

        for class_name in matches:
            plugins.append(
                {
                    "name": name,
                    "package_name": package_name,
                    "dart_dir": dart_dir,
                    "class_name": class_name,
                }
            )

    return plugins


def update_pubspec(plugins):
    """Add/update path dependencies in the frontend's pubspec.yaml."""
    with open(PUBSPEC) as f:
        content = f.read()

    # Build the managed section
    managed_lines = [BEGIN_MARKER]
    seen = set()
    for p in plugins:
        if p["package_name"] not in seen:
            managed_lines.append(f"  {p['package_name']}:")
            managed_lines.append(f"    path: {p['dart_dir']}")
            seen.add(p["package_name"])
    managed_lines.append(END_MARKER)
    managed_block = "\n".join(managed_lines)

    # Replace existing managed section or insert before dev_dependencies
    if BEGIN_MARKER in content:
        content = re.sub(
            re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER),
            managed_block,
            content,
            flags=re.DOTALL,
        )
    else:
        # Insert before dev_dependencies
        content = content.replace(
            "\ndev_dependencies:",
            f"\n{managed_block}\n\ndev_dependencies:",
        )

    with open(PUBSPEC, "w") as f:
        f.write(content)


def generate_dart(plugins):
    """Generate plugins_generated.dart with package imports."""
    lines = [
        "// GENERATED — do not edit. Run `python scripts/import_plugins.py` to regenerate.",
        "import 'package:bark_plugin_api/bark_plugin_api.dart';",
        "",
    ]
    for p in plugins:
        lines.append(f"import 'package:{p['package_name']}/plugin.dart';")

    lines.append("")
    lines.append("List<ToolPlugin> createAllPlugins() {")
    lines.append("  return [")
    for p in plugins:
        lines.append(f"    {p['class_name']}(),")
    lines.append("  ];")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main():
    plugins = find_plugins()

    # Update pubspec.yaml with path dependencies
    update_pubspec(plugins)

    # Generate plugins_generated.dart
    output = generate_dart(plugins)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        f.write(output)

    names = [p["class_name"] for p in plugins]
    print(f"Generated {OUTPUT} with {len(plugins)} plugins: {', '.join(names)}")
    if plugins:
        print(f"Updated {PUBSPEC} with path dependencies")


if __name__ == "__main__":
    main()
