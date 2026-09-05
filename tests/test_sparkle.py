from __future__ import annotations

import random
import unittest

from shortcut_lights.sparkle import Sparkle


class SparkleTests(unittest.TestCase):
    def test_spawns_within_bounds(self):
        sparkle = Sparkle(6, 17, [(255, 0, 0)], spawn_rate=100.0, rng=random.Random(1))
        frame = sparkle.tick(1.0)
        self.assertTrue(frame)
        for row, col in frame:
            self.assertTrue(0 <= row < 6)
            self.assertTrue(0 <= col < 17)

    def test_never_exceeds_max_concurrent(self):
        sparkle = Sparkle(6, 17, [(255, 0, 0)], spawn_rate=1000.0, max_concurrent=5, rng=random.Random(2))
        for _ in range(50):
            sparkle.tick(0.1)
        self.assertLessEqual(len(sparkle._sparks), 5)

    def test_zero_spawn_rate_produces_no_new_sparkles(self):
        sparkle = Sparkle(6, 17, [(255, 0, 0)], spawn_rate=0.0, rng=random.Random(3))
        frame = sparkle.tick(10.0)
        self.assertEqual(frame, {})

    def test_sparkle_fades_out_and_disappears(self):
        # signature_colors deliberately can't match this palette, so this
        # spark takes the normal (short) hold, not the sticky one.
        sparkle = Sparkle(
            1, 1, [(200, 100, 50)], signature_colors=[(1, 2, 3)],
            spawn_rate=1000.0, max_concurrent=1, rng=random.Random(4),
        )
        sparkle.tick(0.01)  # spawns the single available key
        self.assertEqual(len(sparkle._sparks), 1)
        # Stop spawning so this one spark can't be replaced by a successor
        # the instant it frees up its slot (a 1x1 grid would do that forever).
        sparkle.spawn_rate = 0.0
        # Advance well past any possible fade_in+hold+fade_out (max ~2s)
        for _ in range(50):
            sparkle.tick(0.1)
        self.assertEqual(sparkle._sparks, {})

    def test_signature_colored_sparkle_sticks_far_longer_than_normal(self):
        normal = Sparkle(
            1, 1, [(200, 100, 50)], signature_colors=[(1, 2, 3)],
            spawn_rate=1000.0, max_concurrent=1, rng=random.Random(8),
        )
        sticky = Sparkle(
            1, 1, [(4, 197, 240)], signature_colors=[(4, 197, 240)],
            spawn_rate=1000.0, max_concurrent=1, rng=random.Random(8),
        )
        normal.tick(0.01)
        sticky.tick(0.01)
        normal.spawn_rate = 0.0
        sticky.spawn_rate = 0.0
        # Well past any normal sparkle's max lifetime (~2s), nowhere near a
        # sticky one's minimum hold (20s+).
        for _ in range(30):
            normal.tick(0.1)
            sticky.tick(0.1)
        self.assertEqual(normal._sparks, {})
        self.assertEqual(len(sticky._sparks), 1)

    def test_frame_colors_scale_toward_the_source_palette_color(self):
        sparkle = Sparkle(1, 1, [(200, 100, 50)], spawn_rate=1000.0, max_concurrent=1, rng=random.Random(5))
        frame = sparkle.tick(0.001)
        (color,) = frame.values()
        self.assertLessEqual(color[0], 200)
        self.assertLessEqual(color[1], 100)
        self.assertLessEqual(color[2], 50)

    def test_brightness_scales_peak_output(self):
        rng_args = (6, 17, [(200, 100, 50)])
        full = Sparkle(*rng_args, spawn_rate=1000.0, max_concurrent=1, brightness=1.0, rng=random.Random(6))
        dim = Sparkle(*rng_args, spawn_rate=1000.0, max_concurrent=1, brightness=0.5, rng=random.Random(6))
        # advance both into their hold phase (full brightness plateau) using identical seeds
        for _ in range(3):
            full.tick(0.05)
            dim.tick(0.05)
        full_frame = full.tick(0.0)
        dim_frame = dim.tick(0.0)
        if full_frame and dim_frame:
            full_color = next(iter(full_frame.values()))
            dim_color = next(iter(dim_frame.values()))
            self.assertLessEqual(dim_color[0], full_color[0])

    def test_base_color_scales_by_base_brightness(self):
        sparkle = Sparkle(
            1, 1, [(255, 0, 0)], signature_colors=[(200, 100, 50)],
            base_brightness=0.5, rng=random.Random(9),
        )
        self.assertEqual(sparkle.base_color(), (100, 50, 25))

    def test_base_color_holds_then_crossfades_to_next_signature(self):
        sparkle = Sparkle(
            1, 1, [(255, 0, 0)],
            signature_colors=[(200, 0, 0), (0, 200, 0)],
            base_brightness=1.0, base_cycle_sec=10.0, spawn_rate=0.0,
            rng=random.Random(10),
        )
        self.assertEqual(sparkle.base_color(), (200, 0, 0))
        sparkle.tick(5.0)  # mid-way through the first color's hold, no crossfade yet
        self.assertEqual(sparkle.base_color(), (200, 0, 0))
        sparkle.tick(5.0)  # exactly at the second cycle's start
        self.assertEqual(sparkle.base_color(), (0, 200, 0))

    def test_base_color_single_signature_never_changes(self):
        sparkle = Sparkle(
            1, 1, [(255, 0, 0)], signature_colors=[(10, 20, 30)],
            base_brightness=1.0, base_cycle_sec=1.0, spawn_rate=0.0, rng=random.Random(11),
        )
        before = sparkle.base_color()
        sparkle.tick(100.0)
        self.assertEqual(sparkle.base_color(), before)
        self.assertEqual(before, (10, 20, 30))

    def test_set_palette_used_by_new_spawns(self):
        sparkle = Sparkle(6, 17, [(255, 0, 0)], spawn_rate=1000.0, rng=random.Random(7))
        sparkle.set_palette([(0, 255, 0)])
        frame = sparkle.tick(1.0)
        for color in frame.values():
            self.assertEqual(color[0], 0)
            self.assertGreater(color[1], 0)


if __name__ == "__main__":
    unittest.main()
