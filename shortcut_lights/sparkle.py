"""Ambient full-keyboard random-sparkle animation, colored from the theme palette.

Two layers, both theme-driven:

- A solid, bright, high-saturation base color across every key, drawn from the
  theme's most intense (highest-chroma) colors — periodically crossfading
  between them if there's more than one (e.g. cyan <-> magenta).
- Sparkles: random keys flash a random palette color, fade in fast, hold
  briefly, then fade back out — except when a sparkle happens to land on one
  of those same signature colors, in which case it "sticks": it holds at full
  brightness for tens of seconds instead of a fraction of one, so the board
  slowly accumulates a scattering of vivid, long-lived cyan/magenta keys on
  top of the quicker, more varied twinkle of the rest of the palette.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

RGB = tuple[int, int, int]


def _lerp_color(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


@dataclass
class _Spark:
    color: RGB
    fade_in: float
    hold: float
    fade_out: float
    age: float = 0.0

    @property
    def duration(self) -> float:
        return self.fade_in + self.hold + self.fade_out

    def level(self) -> float:
        if self.age < self.fade_in:
            return self.age / self.fade_in if self.fade_in > 0 else 1.0
        if self.age < self.fade_in + self.hold:
            return 1.0
        remaining = self.duration - self.age
        return max(0.0, remaining / self.fade_out) if self.fade_out > 0 else 0.0


class Sparkle:
    """Drives the animation; caller re-renders `tick(dt)`'s frame each pass,
    filling any key `tick()` doesn't mention with `base_color()`."""

    def __init__(
        self,
        rows: int,
        cols: int,
        palette: list[RGB],
        signature_colors: list[RGB] | None = None,
        spawn_rate: float = 4.0,
        max_concurrent: int | None = None,
        brightness: float = 1.0,
        base_brightness: float = 0.9,
        base_cycle_sec: float = 20.0,
        sticky_hold_range: tuple[float, float] = (20.0, 60.0),
        rng: random.Random | None = None,
    ) -> None:
        self.rows = max(1, rows)
        self.cols = max(1, cols)
        self.palette = list(palette) or [(56, 189, 248)]
        self.signature_colors = list(signature_colors) if signature_colors else [self.palette[0]]
        self.spawn_rate = max(0.0, spawn_rate)
        self.max_concurrent = max_concurrent or max(4, (self.rows * self.cols) // 6)
        self.brightness = max(0.0, min(1.0, brightness))
        self.base_brightness = max(0.0, min(1.0, base_brightness))
        self.base_cycle_sec = max(1.0, base_cycle_sec)
        self.sticky_hold_range = sticky_hold_range
        self._rng = rng or random.Random()
        self._sparks: dict[tuple[int, int], _Spark] = {}
        self._spawn_accumulator = 0.0
        self._elapsed = 0.0

    def set_palette(self, palette: list[RGB], signature_colors: list[RGB] | None = None) -> None:
        if palette:
            self.palette = list(palette)
        if signature_colors:
            self.signature_colors = list(signature_colors)

    def base_color(self) -> RGB:
        """The always-on solid color for keys with no active sparkle: bright,
        drawn from the theme's most saturated colors, crossfading between them
        over `base_cycle_sec` each if there's more than one."""
        colors = self.signature_colors
        base = colors[0]
        if len(colors) > 1:
            cycle_len = self.base_cycle_sec * len(colors)
            position = self._elapsed % cycle_len
            index = int(position // self.base_cycle_sec)
            progress = (position % self.base_cycle_sec) / self.base_cycle_sec
            transition = 0.2  # fraction of each color's window spent crossfading out
            hold_until = 1.0 - transition
            if progress >= hold_until:
                next_color = colors[(index + 1) % len(colors)]
                base = _lerp_color(colors[index], next_color, (progress - hold_until) / transition)
            else:
                base = colors[index]
        return tuple(round(channel * self.base_brightness) for channel in base)

    def _spawn(self) -> None:
        capacity = min(self.max_concurrent, self.rows * self.cols)
        if len(self._sparks) >= capacity:
            return
        for _ in range(20):  # a handful of random probes beats scanning every key
            key = (self._rng.randrange(self.rows), self._rng.randrange(self.cols))
            if key in self._sparks:
                continue
            color = self._rng.choice(self.palette)
            sticky = color in self.signature_colors
            hold = (
                self._rng.uniform(*self.sticky_hold_range)
                if sticky
                else self._rng.uniform(0.05, 0.4)
            )
            self._sparks[key] = _Spark(
                color=color,
                fade_in=self._rng.uniform(0.08, 0.25),
                hold=hold,
                fade_out=self._rng.uniform(0.5, 1.4),
            )
            return

    def tick(self, dt: float) -> dict[tuple[int, int], RGB]:
        """Advance by dt seconds and return this frame's {(row, col): rgb} for
        keys with an active sparkle. Every other key should be painted with
        `base_color()`."""
        dt = max(0.0, dt)
        self._elapsed += dt
        self._spawn_accumulator += dt * self.spawn_rate
        while self._spawn_accumulator >= 1.0:
            self._spawn()
            self._spawn_accumulator -= 1.0

        frame: dict[tuple[int, int], RGB] = {}
        finished = []
        for key, spark in self._sparks.items():
            spark.age += dt
            level = spark.level() * self.brightness
            if spark.age >= spark.duration or level <= 0.0:
                finished.append(key)
                continue
            r, g, b = spark.color
            frame[key] = (round(r * level), round(g * level), round(b * level))
        for key in finished:
            del self._sparks[key]
        return frame
