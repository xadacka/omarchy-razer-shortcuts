#!/usr/bin/env python3
"""CLI entry point for Razer Shortcut Lights."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from shortcut_lights.runtime import DEFAULT_CONFIG, keyboard_paths, load_config, read_bindings, run


def config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "omarchy" / "razer-shortcuts.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Light active Omarchy shortcuts on an OpenRazer keyboard")
    parser.add_argument("command", choices=("run", "doctor", "bindings", "init-config"), nargs="?", default="run")
    args = parser.parse_args()
    try:
        if args.command == "run":
            return run(config_path())
        if args.command == "bindings":
            print(json.dumps({str(mask): sorted(keys) for mask, keys in read_bindings().items()}, indent=2))
            return 0
        if args.command == "init-config":
            path = config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
            print(path)
            return 0
        import openrazer.client

        config = load_config(config_path())
        bindings = read_bindings()
        paths = keyboard_paths()
        readable = []
        for path in paths:
            try:
                with path.open("rb", buffering=0):
                    readable.append(str(path))
            except OSError:
                pass
        manager = openrazer.client.DeviceManager()
        devices = [
            {
                "name": str(device.name),
                "serial": str(device.serial),
                "matrix": f"{device.fx.advanced.rows}x{device.fx.advanced.cols}",
            }
            for device in manager.devices
            if getattr(getattr(device, "fx", None), "advanced", None)
        ]
        report = {
            "ok": bool(devices and readable and bindings),
            "config": config,
            "configPath": str(config_path()),
            "inputDevices": [str(path) for path in paths],
            "readableInputDevices": readable,
            "openRazerDevices": devices,
            "shortcutSets": {str(mask): len(keys) for mask, keys in bindings.items()},
        }
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1
    except Exception as error:
        print(f"razer-shortcut-lights: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
