"""Linux input, Hyprland binding, and OpenRazer runtime adapters."""

from __future__ import annotations

import glob
import json
import os
import selectors
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .core import active_targets, parse_binding_lines
from .layouts import BLADE_16_6X17, MODIFIER_BITS, MODIFIER_EVENT_CODES


EVENT = struct.Struct("llHHI")
EV_KEY = 1
DEFAULT_CONFIG = {
    "activeColor": "#38bdf8",
    "modifierColor": "#ffffff",
    "includeModifierKeys": True,
    "refreshBindingsSec": 10,
    "deviceSerial": "auto",
}


def log(message: str) -> None:
    print(f"razer-shortcut-lights: {message}", file=sys.stderr, flush=True)


def load_config(path: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            user_config = json.load(handle)
        if isinstance(user_config, dict):
            config.update(user_config)
    return config


def rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def read_bindings() -> dict[int, set[str]]:
    result = subprocess.run(
        ["omarchy", "menu", "keybindings", "--print"],
        check=True, capture_output=True, text=True, timeout=8,
    )
    return parse_binding_lines(result.stdout)


def keyboard_paths() -> list[Path]:
    candidates = []
    for pattern in (
        "/dev/input/by-id/usb-Razer_*-event-kbd",
        "/dev/input/by-id/usb-Razer_*-if*-event-kbd",
    ):
        for path in sorted(glob.glob(pattern)):
            resolved = Path(path).resolve()
            if resolved not in candidates:
                candidates.append(resolved)
    return candidates


def select_device(manager: Any, serial: str) -> Any:
    devices = [dev for dev in manager.devices if getattr(getattr(dev, "fx", None), "advanced", None)]
    if serial != "auto":
        devices = [dev for dev in devices if str(getattr(dev, "serial", "")).lower() == serial.lower()]
    if not devices:
        raise RuntimeError("no OpenRazer per-key keyboard found")
    return devices[0]


class Lighting:
    def __init__(self, device: Any, config: dict[str, Any]) -> None:
        self.device = device
        self.matrix = device.fx.advanced.matrix
        self.rows = int(device.fx.advanced.rows)
        self.cols = int(device.fx.advanced.cols)
        if (self.rows, self.cols) != (6, 17):
            raise RuntimeError(f"unsupported matrix {self.rows}x{self.cols}; add a layout adapter")
        self.active_rgb = rgb(str(config["activeColor"]))
        self.modifier_rgb = rgb(str(config["modifierColor"]))
        self.include_modifiers = bool(config["includeModifierKeys"])
        self.restore_effect = str(getattr(device.fx, "effect", "spectrum") or "spectrum")
        raw_colors = bytes(getattr(device.fx, "colors", b"") or b"")
        self.restore_colors = [tuple(raw_colors[index:index + 3]) for index in range(0, len(raw_colors), 3)]
        self.restore_colors = [color for color in self.restore_colors if len(color) == 3]
        self.restore_brightness = getattr(device, "brightness", None)

    def paint(self, targets: set[str], held_names: set[str]) -> None:
        for row in range(self.rows):
            for col in range(self.cols):
                self.matrix[row, col] = (0, 0, 0)
        for target in targets:
            if target in BLADE_16_6X17:
                self.matrix[BLADE_16_6X17[target]] = self.active_rgb
        if self.include_modifiers:
            modifier_keys = {
                "SUPER": "LEFTMETA", "ALT": "LEFTALT",
                "CTRL": "LEFTCTRL", "SHIFT": "LEFTSHIFT",
            }
            for name in held_names:
                target = modifier_keys[name]
                if target in BLADE_16_6X17:
                    self.matrix[BLADE_16_6X17[target]] = self.modifier_rgb
        self.device.fx.advanced.draw()

    def restore(self) -> None:
        fx = self.device.fx
        effect = self.restore_effect.lower()
        try:
            colors = self.restore_colors or [self.active_rgb]
            first = colors[0]
            second = colors[1] if len(colors) > 1 else first
            if effect in {"none", "off"}:
                fx.none()
            elif effect == "static":
                fx.static(*first)
            elif effect == "wave":
                fx.wave(1)
            elif effect == "breath_single":
                fx.breath_single(*first)
            elif effect == "breath_dual":
                fx.breath_dual(*first, *second)
            elif effect.startswith("breath"):
                fx.breath_random()
            elif effect == "starlight_single":
                fx.starlight_single(*first, 2)
            elif effect == "starlight_dual":
                fx.starlight_dual(*first, *second, 2)
            elif effect.startswith("starlight"):
                fx.starlight_random(2)
            elif effect == "ripple":
                fx.ripple(*first)
            elif effect.startswith("ripple"):
                fx.ripple_random()
            elif effect == "reactive":
                fx.reactive(*first, 2)
            else:
                fx.spectrum()
            if self.restore_brightness is not None:
                self.device.brightness = self.restore_brightness
        except Exception as error:
            log(f"could not restore {effect} effect: {error}")


def run(config_path: Path) -> int:
    import openrazer.client

    config = load_config(config_path)
    manager = openrazer.client.DeviceManager()
    lighting = Lighting(select_device(manager, str(config["deviceSerial"])), config)
    paths = keyboard_paths()
    if not paths:
        raise RuntimeError("no Razer keyboard input event device found")

    selector = selectors.DefaultSelector()
    handles = []
    for path in paths:
        try:
            handle = path.open("rb", buffering=0)
        except PermissionError:
            continue
        handles.append(handle)
        selector.register(handle, selectors.EVENT_READ)
    if not handles:
        raise RuntimeError("Razer keyboard events are not readable; check OpenRazer group permissions")

    bindings = read_bindings()
    refresh_sec = max(2, int(config["refreshBindingsSec"]))
    last_refresh = time.monotonic()
    # Keep state per HID interface. Blade firmware revisions can route modifiers
    # through either interface, and some report them through both.
    held_by_handle: dict[Any, set[int]] = {handle: set() for handle in handles}
    last_mask = 0
    stopping = False

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log(f"watching {', '.join(str(path) for path in paths)} for {lighting.device.name}")

    try:
        while not stopping:
            now = time.monotonic()
            if not any(held_by_handle.values()) and now - last_refresh >= refresh_sec:
                try:
                    bindings = read_bindings()
                    last_refresh = now
                except Exception as error:
                    log(f"binding refresh failed: {error}")
            for key, _mask in selector.select(timeout=0.25):
                data = key.fileobj.read(EVENT.size)
                if len(data) != EVENT.size:
                    continue
                _sec, _usec, event_type, code, value = EVENT.unpack(data)
                if event_type != EV_KEY or code not in MODIFIER_EVENT_CODES or value == 2:
                    continue
                source_held = held_by_handle[key.fileobj]
                if value == 1:
                    source_held.add(code)
                elif value == 0:
                    source_held.discard(code)
                held_codes = set().union(*held_by_handle.values())
                held_names = {MODIFIER_EVENT_CODES[item] for item in held_codes}
                held_mask = sum(MODIFIER_BITS[name] for name in held_names)
                if held_mask == last_mask:
                    continue
                last_mask = held_mask
                if held_mask:
                    lighting.paint(active_targets(bindings, held_mask), held_names)
                else:
                    lighting.restore()
    finally:
        if last_mask:
            lighting.restore()
        for handle in handles:
            handle.close()
    return 0
