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
from .apps import application_targets
from .layouts import MODIFIER_BITS, MODIFIER_EVENT_CODES, STANDARD_KEYBOARD
from .sparkle import Sparkle
from . import theme


EVENT = struct.Struct("llHHI")
EV_KEY = 1
# activeColor/modifierColor/layerColors/modifierKeyColors below are only the
# fallback used when the theme has no colors.toml to derive from (see
# theme.derive_colors, fed only the theme's most intense colors — see
# modifierIntenseCount below — and applied on top of these in run()). Any of
# these four keys set explicitly in the user's config file are never
# overridden by the theme — see explicit_config_keys().
DEFAULT_CONFIG = {
    "activeColor": "#38bdf8",
    "modifierColor": "#ffffff",
    "layerColors": {
        "SUPER": "#38bdf8",
        "ALT": "#e879f9",
        "CTRL": "#fbbf24",
        "SUPER+SHIFT": "#f97316",
        "SUPER+ALT": "#f472b6",
        "SUPER+CTRL": "#a78bfa",
        "SHIFT+ALT": "#fb7185",
        "CTRL+ALT": "#34d399",
        "SUPER+SHIFT+ALT": "#ef4444",
        "SUPER+SHIFT+CTRL": "#84cc16",
        "SUPER+CTRL+ALT": "#22d3ee",
        "SHIFT+CTRL+ALT": "#facc15",
        "SUPER+SHIFT+CTRL+ALT": "#ffffff"
    },
    "modifierKeyColors": {
        "SUPER": "#38bdf8",
        "SHIFT": "#f97316",
        "CTRL": "#fbbf24",
        "ALT": "#e879f9"
    },
    "shiftAloneMode": "invert",
    "applicationShortcuts": True,
    "includeModifierKeys": True,
    "refreshBindingsSec": 10,
    "deviceSerial": "auto",
    # How many of the theme's most saturated colors activeColor, modifierColor,
    # layerColors, and modifierKeyColors are derived from — keeps every
    # shortcut-overlay color vivid, not just the sparkle base layer.
    "modifierIntenseCount": 8,
    # Resting state (i.e. no modifier held): "sparkle" (ambient themed
    # twinkle, the default), "static" (flat theme accent color), or
    # "previousEffect" (restore whatever native OpenRazer effect was active
    # before the daemon started painting overlays — the original behavior).
    "restingMode": "sparkle",
    "sparkleFps": 24,
    "sparkleSpawnRate": 4.0,
    "sparkleMaxConcurrent": None,
    "sparkleBrightness": 100,
    # How many of the theme's most saturated ("signature") colors the base
    # layer cycles through, and which sparkle colors "stick" (see below).
    "sparkleSignatureCount": 2,
    # Solid, bright, high-saturation wash under the sparkle animation, drawn
    # from the theme's signature colors (% brightness) — resting keys are
    # always a visible solid color, never black. Black is reserved for the
    # shortcut overlay, where it makes the held-modifier's targets pop.
    "sparkleBaseBrightness": 90,
    # Seconds spent on each signature color before crossfading to the next
    # (only matters when sparkleSignatureCount > 1).
    "sparkleBaseCycleSec": 20.0,
    # A sparkle that happens to land on a signature color holds at full
    # brightness for a random duration in this range (seconds) instead of a
    # normal sparkle's fraction-of-a-second hold, before fading out like any
    # other — so the board slowly accumulates long-lived vivid highlights.
    "sparkleStickyMinSec": 20.0,
    "sparkleStickyMaxSec": 60.0,
    "themeRefreshSec": 5,
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


def explicit_config_keys(path: Path) -> set[str]:
    """Top-level keys the user actually set in their config file, so theme-derived
    colors never clobber an explicit override."""
    if not path.exists():
        return set()
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return set()
    return set(data) if isinstance(data, dict) else set()


def rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def invert(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(255 - channel for channel in color)


def layer_name(held_names: set[str]) -> str:
    order = ("SUPER", "SHIFT", "CTRL", "ALT")
    return "+".join(name for name in order if name in held_names)


def read_bindings() -> dict[int, set[str]]:
    result = subprocess.run(
        ["omarchy", "menu", "keybindings", "--print"],
        check=True, capture_output=True, text=True, timeout=8,
    )
    return parse_binding_lines(result.stdout)


def active_window_class() -> str:
    try:
        result = subprocess.run(
            ["hyprctl", "activewindow", "-j"],
            check=True, capture_output=True, text=True, timeout=1,
        )
        data = json.loads(result.stdout)
        return str(data.get("class", ""))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return ""


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
        if self.rows < 5 or self.cols < 14:
            raise RuntimeError(
                f"matrix {self.rows}x{self.cols} does not use OpenRazer's standard keyboard layout"
            )
        self._load_colors(config)
        self.shift_alone_mode = str(config.get("shiftAloneMode", "invert"))
        self.include_modifiers = bool(config["includeModifierKeys"])
        self.resting_mode = str(config.get("restingMode", "sparkle"))
        if self.resting_mode == "previousEffect":
            self.snapshot()

    def _load_colors(self, config: dict[str, Any]) -> None:
        self.active_rgb = rgb(str(config["activeColor"]))
        self.modifier_rgb = rgb(str(config["modifierColor"]))
        self.layer_colors = {
            str(name): rgb(str(color))
            for name, color in dict(config.get("layerColors", {})).items()
        }
        self.modifier_colors = {
            str(name): rgb(str(color))
            for name, color in dict(config.get("modifierKeyColors", {})).items()
        }

    def update_theme_colors(self, derived: dict[str, Any], locked_keys: set[str]) -> None:
        """Refresh theme-derived colors after a live theme change, leaving any
        color the user explicitly set in their config file untouched."""
        if "activeColor" not in locked_keys:
            self.active_rgb = rgb(str(derived["activeColor"]))
        if "modifierColor" not in locked_keys:
            self.modifier_rgb = rgb(str(derived["modifierColor"]))
        if "layerColors" not in locked_keys:
            self.layer_colors = {
                str(name): rgb(str(color)) for name, color in derived["layerColors"].items()
            }
        if "modifierKeyColors" not in locked_keys:
            self.modifier_colors = {
                str(name): rgb(str(color)) for name, color in derived["modifierKeyColors"].items()
            }

    def snapshot(self) -> None:
        # Captures whatever is currently lit so restore() can put it back.
        # Must be called fresh before each paint(), not just once at
        # startup: this process stays running for the whole session (see
        # Service.qml, kept loaded), so a one-time snapshot at __init__
        # would go stale the moment anything else (a theme change, the
        # OpenRazer panel, etc.) re-lights the keyboard afterward.
        fx = self.device.fx
        self.restore_effect = str(getattr(fx, "effect", "spectrum") or "spectrum")
        raw_colors = bytes(getattr(fx, "colors", b"") or b"")
        colors = [tuple(raw_colors[index:index + 3]) for index in range(0, len(raw_colors), 3)]
        self.restore_colors = [color for color in colors if len(color) == 3]
        self.restore_brightness = getattr(self.device, "brightness", None)

    def draw_frame(
        self,
        pixels: dict[tuple[int, int], tuple[int, int, int]],
        default: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """Paint an explicit {(row, col): rgb} frame; every other key gets `default`."""
        for row in range(self.rows):
            for col in range(self.cols):
                self.matrix[row, col] = pixels.get((row, col), default)
        self.device.fx.advanced.draw()

    def static_theme(self) -> None:
        try:
            self.device.fx.static(*self.active_rgb)
        except Exception as error:
            log(f"could not apply static theme color: {error}")

    def paint(self, targets: set[str], held_names: set[str]) -> None:
        pixels: dict[tuple[int, int], tuple[int, int, int]] = {}
        target_rgb = self.layer_colors.get(layer_name(held_names), self.active_rgb)
        if held_names == {"SHIFT"} and self.shift_alone_mode == "invert":
            targets = set(STANDARD_KEYBOARD)
            target_rgb = invert(self.active_rgb)
        for target in targets:
            coordinate = STANDARD_KEYBOARD.get(target)
            if coordinate and coordinate[0] < self.rows and coordinate[1] < self.cols:
                pixels[coordinate] = target_rgb
        if self.include_modifiers:
            modifier_keys = {
                "SUPER": "LEFTMETA", "ALT": "LEFTALT",
                "CTRL": "LEFTCTRL", "SHIFT": "LEFTSHIFT",
            }
            for name in held_names:
                target = modifier_keys[name]
                coordinate = STANDARD_KEYBOARD.get(target)
                if coordinate and coordinate[0] < self.rows and coordinate[1] < self.cols:
                    pixels[coordinate] = self.modifier_colors.get(name, self.modifier_rgb)
        self.draw_frame(pixels)

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
    locked_keys = explicit_config_keys(config_path)

    vibrant = theme.vibrant_colors(theme.load_palette())
    signature = theme.intense_colors(vibrant, count=max(1, int(config.get("sparkleSignatureCount", 2))))
    modifier_palette = theme.intense_colors(
        vibrant, count=max(1, int(config.get("modifierIntenseCount", 8)))
    )
    derived_colors = theme.derive_colors(modifier_palette)
    for key, value in derived_colors.items():
        if key not in locked_keys:
            config[key] = value

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
    theme_refresh_sec = max(1, int(config.get("themeRefreshSec", 5)))
    app_shortcuts_enabled = bool(config.get("applicationShortcuts", True))
    resting_mode = str(config.get("restingMode", "sparkle"))

    sparkle: Sparkle | None = None
    frame_interval = 0.25
    if resting_mode == "sparkle":
        fps = max(1, int(config.get("sparkleFps", 24)))
        frame_interval = 1.0 / fps
        sparkle = Sparkle(
            lighting.rows,
            lighting.cols,
            vibrant,
            signature_colors=signature,
            spawn_rate=float(config.get("sparkleSpawnRate", 4.0)),
            max_concurrent=config.get("sparkleMaxConcurrent"),
            brightness=max(0, min(100, int(config.get("sparkleBrightness", 100)))) / 100.0,
            base_brightness=max(0, min(100, int(config.get("sparkleBaseBrightness", 90)))) / 100.0,
            base_cycle_sec=float(config.get("sparkleBaseCycleSec", 20.0)),
            sticky_hold_range=(
                float(config.get("sparkleStickyMinSec", 20.0)),
                float(config.get("sparkleStickyMaxSec", 60.0)),
            ),
        )
    elif resting_mode != "previousEffect":
        lighting.static_theme()

    last_refresh = time.monotonic()
    last_theme_check = last_refresh
    last_theme_mtime = theme.mtime()
    last_frame = last_refresh
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
    log(f"watching {', '.join(str(path) for path in paths)} for {lighting.device.name}, resting mode: {resting_mode}")

    try:
        while not stopping:
            now = time.monotonic()
            if not any(held_by_handle.values()) and now - last_refresh >= refresh_sec:
                try:
                    bindings = read_bindings()
                    last_refresh = now
                except Exception as error:
                    log(f"binding refresh failed: {error}")

            if now - last_theme_check >= theme_refresh_sec:
                last_theme_check = now
                new_mtime = theme.mtime()
                if new_mtime != last_theme_mtime:
                    last_theme_mtime = new_mtime
                    vibrant = theme.vibrant_colors(theme.load_palette())
                    signature = theme.intense_colors(
                        vibrant, count=max(1, int(config.get("sparkleSignatureCount", 2)))
                    )
                    modifier_palette = theme.intense_colors(
                        vibrant, count=max(1, int(config.get("modifierIntenseCount", 8)))
                    )
                    lighting.update_theme_colors(theme.derive_colors(modifier_palette), locked_keys)
                    if sparkle is not None:
                        sparkle.set_palette(vibrant, signature)
                    elif resting_mode != "previousEffect" and not last_mask:
                        lighting.static_theme()
                    log("theme changed; refreshed keyboard colors")

            # Poll fast enough for smooth sparkle frames while idle; a held
            # modifier is already fully event-driven, so back off and just
            # wait for the next key event.
            timeout = frame_interval if (sparkle is not None and not last_mask) else 0.25
            for key, _mask in selector.select(timeout=timeout):
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
                entering_hold = last_mask == 0 and held_mask != 0
                last_mask = held_mask
                if held_mask:
                    if entering_hold and resting_mode == "previousEffect":
                        lighting.snapshot()
                    targets = active_targets(bindings, held_mask)
                    if app_shortcuts_enabled:
                        targets |= application_targets(active_window_class(), held_mask)
                    lighting.paint(targets, held_names)
                elif resting_mode == "previousEffect":
                    lighting.restore()
                elif resting_mode != "sparkle":
                    # "static", or any unrecognized value — fall back to a
                    # flat theme color rather than leaving the board on its
                    # blacked-out overlay frame.
                    lighting.static_theme()
                # resting_mode == "sparkle": nothing to do here — the tick
                # below repaints the very next pass through this loop.

            if sparkle is not None and not last_mask:
                frame_now = time.monotonic()
                dt = min(max(0.0, frame_now - last_frame), 0.5)
                last_frame = frame_now
                lighting.draw_frame(sparkle.tick(dt), default=sparkle.base_color())
            else:
                last_frame = time.monotonic()
    finally:
        if resting_mode == "previousEffect":
            if last_mask:
                lighting.restore()
        else:
            # Leave a clean flat theme color rather than freezing on
            # whatever the sparkle animation (or a blacked-out overlay
            # frame) happened to be drawing at the moment we were stopped.
            lighting.static_theme()
        for handle in handles:
            handle.close()
    return 0
