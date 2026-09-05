from __future__ import annotations

import unittest

from shortcut_lights import theme


class VibrantColorsTests(unittest.TestCase):
    def test_drops_near_black_and_near_white(self):
        palette = {
            "accent": (190, 63, 80),
            "color0": (0, 0, 0),
            "color1": (255, 255, 255),
            "color2": (226, 3, 66),
        }
        result = theme.vibrant_colors(palette)
        self.assertIn((190, 63, 80), result)
        self.assertIn((226, 3, 66), result)
        self.assertNotIn((0, 0, 0), result)
        self.assertNotIn((255, 255, 255), result)

    def test_accent_is_preferred_first(self):
        palette = {"accent": (190, 63, 80), "color4": (190, 63, 80), "color2": (226, 3, 66)}
        result = theme.vibrant_colors(palette)
        self.assertEqual(result[0], (190, 63, 80))
        # accent and color4 are identical, so the duplicate is dropped
        self.assertEqual(len(result), 2)

    def test_works_with_a_non_color_n_theme_schema(self):
        # Some community Omarchy themes name channels directly (red/yellow/
        # green/cyan/... plus bright_* variants) instead of color0-color15 —
        # this must not degrade to just "accent".
        palette = {
            "accent": (0x50, 0x94, 0x75),
            "background": (0x11, 0x1C, 0x18),
            "dark_background": (0x0C, 0x15, 0x12),
            "selection": (0x32, 0x47, 0x3B),
            "muted": (0x53, 0x68, 0x5B),
            "foreground": (0xC1, 0xC4, 0x97),
            "red": (0xFF, 0x53, 0x45),
            "cyan": (0x2D, 0xD5, 0xB7),
            "bright_yellow": (0xE5, 0xC7, 0x36),
        }
        result = theme.vibrant_colors(palette)
        self.assertIn((0xFF, 0x53, 0x45), result)
        self.assertIn((0x2D, 0xD5, 0xB7), result)
        self.assertIn((0xE5, 0xC7, 0x36), result)
        # structural keys stay excluded regardless of schema
        self.assertNotIn((0x11, 0x1C, 0x18), result)
        self.assertNotIn((0x32, 0x47, 0x3B), result)
        self.assertNotIn((0x53, 0x68, 0x5B), result)

    def test_empty_palette_falls_back(self):
        result = theme.vibrant_colors({})
        self.assertEqual(result, list(theme.FALLBACK_PALETTE))

    def test_all_dropped_falls_back_to_accent(self):
        result = theme.vibrant_colors({"accent": (0, 0, 0), "foreground": (20, 185, 181)})
        self.assertEqual(result, [(20, 185, 181)])


class LoadPaletteTests(unittest.TestCase):
    def test_missing_file_returns_empty(self, ):
        from pathlib import Path

        self.assertEqual(theme.load_palette(Path("/nonexistent/colors.toml")), {})

    def test_parses_hex_strings_only(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "colors.toml"
            path.write_text('accent = "#BE3F50"\ncursor = "#ff7f41"\ncount = 4\n')
            palette = theme.load_palette(path)
            self.assertEqual(palette["accent"], (0xBE, 0x3F, 0x50))
            self.assertEqual(palette["cursor"], (0xFF, 0x7F, 0x41))
            self.assertNotIn("count", palette)


class IntenseColorsTests(unittest.TestCase):
    def test_ranks_by_chroma_not_input_order(self):
        # Mirrors the real aetheria theme: a muted accent, plus a vivid cyan
        # and a vivid crimson buried later in the list.
        colors = [(190, 63, 80), (200, 233, 103), (4, 197, 240), (226, 3, 66)]
        result = theme.intense_colors(colors, count=2)
        self.assertEqual(result, [(4, 197, 240), (226, 3, 66)])

    def test_dark_saturated_color_still_ranks_below_a_bright_one(self):
        # (128, 0, 0) is fully saturated but dark; (255, 60, 60) is brighter
        # and should read as more "intense" despite lower raw saturation.
        result = theme.intense_colors([(128, 0, 0), (255, 60, 60)], count=1)
        self.assertEqual(result, [(255, 60, 60)])

    def test_deduplicates_identical_colors(self):
        result = theme.intense_colors([(4, 197, 240), (4, 197, 240), (226, 3, 66)], count=2)
        self.assertEqual(result, [(4, 197, 240), (226, 3, 66)])

    def test_count_larger_than_input_returns_all(self):
        result = theme.intense_colors([(4, 197, 240)], count=2)
        self.assertEqual(result, [(4, 197, 240)])

    def test_empty_input_falls_back(self):
        result = theme.intense_colors([], count=2)
        self.assertEqual(result, list(theme.FALLBACK_PALETTE[:2]))


class DeriveColorsTests(unittest.TestCase):
    def test_deterministic_across_calls(self):
        vibrant = [(20, 185, 181), (253, 62, 106), (255, 127, 65), (226, 3, 66)]
        first = theme.derive_colors(vibrant)
        second = theme.derive_colors(vibrant)
        self.assertEqual(first, second)

    def test_covers_every_layer_combo_and_modifier(self):
        vibrant = [(20, 185, 181), (253, 62, 106)]
        derived = theme.derive_colors(vibrant)
        self.assertEqual(set(derived["layerColors"]), set(theme.LAYER_COMBOS))
        self.assertEqual(set(derived["modifierKeyColors"]), set(theme.MODIFIER_NAMES))
        for value in derived["layerColors"].values():
            self.assertRegex(value, r"^#[0-9a-f]{6}$")

    def test_single_color_palette_still_works(self):
        derived = theme.derive_colors([(20, 185, 181)])
        self.assertEqual(derived["activeColor"], "#14b9b5")
        self.assertTrue(all(value == "#14b9b5" for value in derived["layerColors"].values()))

    def test_empty_palette_uses_fallback(self):
        derived = theme.derive_colors([])
        self.assertEqual(derived["activeColor"], "#{:02x}{:02x}{:02x}".format(*theme.FALLBACK_PALETTE[0]))


if __name__ == "__main__":
    unittest.main()
