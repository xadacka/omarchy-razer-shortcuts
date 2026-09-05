"""Reads the active Omarchy theme's color palette and derives keyboard colors from it."""

from __future__ import annotations

import os
import tomllib
import zlib
from pathlib import Path
from typing import Any

# Modifier-layer combos that DEFAULT_CONFIG assigns colors to (see runtime.py).
# Kept here, not imported from runtime, to avoid a runtime<->theme import cycle.
LAYER_COMBOS = (
    "SUPER", "ALT", "CTRL",
    "SUPER+SHIFT", "SUPER+ALT", "SUPER+CTRL",
    "SHIFT+ALT", "CTRL+ALT",
    "SUPER+SHIFT+ALT", "SUPER+SHIFT+CTRL", "SUPER+CTRL+ALT", "SHIFT+CTRL+ALT",
    "SUPER+SHIFT+CTRL+ALT",
)
MODIFIER_NAMES = ("SUPER", "SHIFT", "CTRL", "ALT")

# Used when a theme has no colors.toml (or none of its colors pass the vibrancy filter).
FALLBACK_PALETTE: tuple[tuple[int, int, int], ...] = (
    (56, 189, 248), (232, 121, 249), (251, 191, 36), (249, 115, 22), (52, 211, 153),
)


def theme_dir() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return root / "omarchy" / "current" / "theme"


def colors_toml_path() -> Path:
    return theme_dir() / "colors.toml"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(value: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*value)


def load_palette(path: Path | None = None) -> dict[str, tuple[int, int, int]]:
    """Load a theme's colors.toml as name -> RGB. Missing/unreadable file -> {}."""
    path = path or colors_toml_path()
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}

    palette: dict[str, tuple[int, int, int]] = {}
    for name, value in data.items():
        if isinstance(value, str) and value.startswith("#"):
            try:
                palette[name] = _hex_to_rgb(value)
            except ValueError:
                continue
    return palette


def _luminance(color: tuple[int, int, int]) -> float:
    r, g, b = color
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# Key-name substrings that mark a palette entry as structural (background,
# selection highlight, a deliberately desaturated "muted" tone) rather than an
# actual accent/text/ANSI color — excluded regardless of theme schema.
# Omarchy themes vary in their colors.toml conventions: some use color0-color15
# (aetheria, sunset-drive), others name channels directly (red/yellow/green/
# cyan/blue/magenta/bright_*, seen on at least one community theme) — so rather
# than hunting for specific key names, every remaining hex value in the file is
# a candidate, and this exclusion list is what keeps backgrounds out regardless
# of which schema is in play.
_STRUCTURAL_KEY_SUBSTRINGS = ("background", "selection")
_STRUCTURAL_KEYS_EXACT = {"muted"}


def vibrant_colors(
    palette: dict[str, tuple[int, int, int]],
    min_luminance: float = 40.0,
    max_luminance: float = 235.0,
) -> list[tuple[int, int, int]]:
    """Pick the theme's saturated colors, dropping near-black/near-white ones
    that would make the keyboard look dim or washed out."""
    # "accent" first only for stable dedup ordering when a schema defines the
    # same color under multiple keys — selection itself is unordered.
    ordered_keys = ["accent"] + [key for key in palette if key != "accent"]
    seen: set[tuple[int, int, int]] = set()
    result: list[tuple[int, int, int]] = []
    for key in ordered_keys:
        if key in _STRUCTURAL_KEYS_EXACT or any(s in key for s in _STRUCTURAL_KEY_SUBSTRINGS):
            continue
        color = palette.get(key)
        if color is None or color in seen:
            continue
        if not (min_luminance <= _luminance(color) <= max_luminance):
            continue
        seen.add(color)
        result.append(color)

    if result:
        return result

    # Every candidate got filtered out (a near-monochrome theme) — reach for
    # *something* non-black before giving up to the hardcoded fallback.
    # `color and color != (0, 0, 0)` avoids the classic bug of treating an
    # actual black tuple as falsy-but-present.
    for key in ("accent", "foreground"):
        color = palette.get(key)
        if color and color != (0, 0, 0):
            return [color]
    return list(FALLBACK_PALETTE)


def _chroma(color: tuple[int, int, int]) -> int:
    # max-min channel spread: rises with both saturation and brightness, which
    # is exactly what "most intense color" means visually — a dark-but-pure
    # hue reads as muddy, not intense, so pure saturation (HSV S) alone would
    # rank it too high.
    return max(color) - min(color)


def intense_colors(
    colors: list[tuple[int, int, int]], count: int = 2
) -> list[tuple[int, int, int]]:
    """Pick the `count` most saturated/vivid colors out of an already-vibrant
    list, ranked by chroma. Used for the sparkle animation's solid base layer
    and for which sparkle colors "stick" instead of fading out."""
    if not colors:
        return list(FALLBACK_PALETTE[:count]) or list(FALLBACK_PALETTE)
    ranked = sorted(colors, key=_chroma, reverse=True)
    result: list[tuple[int, int, int]] = []
    for color in ranked:
        if color not in result:
            result.append(color)
        if len(result) >= count:
            break
    return result


def _stable_index(key: str, length: int) -> int:
    return zlib.crc32(key.encode("utf-8")) % length


def derive_colors(vibrant: list[tuple[int, int, int]]) -> dict[str, Any]:
    """Build activeColor/modifierColor/layerColors/modifierKeyColors from a palette,
    in the same shape as DEFAULT_CONFIG, so it can be merged straight into it."""
    colors = list(vibrant) or list(FALLBACK_PALETTE)
    layer_colors = {
        combo: _rgb_to_hex(colors[_stable_index(combo, len(colors))])
        for combo in LAYER_COMBOS
    }
    modifier_key_colors = {
        name: _rgb_to_hex(colors[index % len(colors)])
        for index, name in enumerate(MODIFIER_NAMES)
    }
    return {
        "activeColor": _rgb_to_hex(colors[0]),
        "modifierColor": _rgb_to_hex(colors[1 % len(colors)]),
        "layerColors": layer_colors,
        "modifierKeyColors": modifier_key_colors,
    }


def mtime(path: Path | None = None) -> float:
    path = path or colors_toml_path()
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0
