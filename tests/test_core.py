from __future__ import annotations

import unittest

from shortcut_lights.core import active_targets, parse_binding_lines
from shortcut_lights.runtime import invert, layer_name
from shortcut_lights.layouts import STANDARD_KEYBOARD


class BindingParserTests(unittest.TestCase):
    def test_groups_by_exact_modifier_mask(self):
        output = """
SUPER + K                           → Keybindings
SUPER SHIFT + F                     → File manager
SHIFT ALT + D                       → Download Video from Web App
XF86AudioMute                       → Mute
"""
        parsed = parse_binding_lines(output)
        self.assertEqual(parsed[64], {"K"})
        self.assertEqual(parsed[65], {"F"})
        self.assertEqual(parsed[9], {"D"})
        self.assertNotIn(0, parsed)

    def test_code_bindings_are_normalized(self):
        parsed = parse_binding_lines("SUPER + code:10 → Workspace 1\n")
        self.assertEqual(parsed[64], {"1"})

    def test_exact_modifiers_only(self):
        bindings = {64: {"K"}, 65: {"F"}}
        self.assertEqual(active_targets(bindings, 65), {"F"})

    def test_layer_name_has_stable_order(self):
        self.assertEqual(layer_name({"ALT", "SUPER", "SHIFT"}), "SUPER+SHIFT+ALT")

    def test_color_inversion(self):
        self.assertEqual(invert((56, 189, 248)), (199, 66, 7))

    def test_standard_layout_covers_full_size_navigation_and_numpad(self):
        self.assertEqual(STANDARD_KEYBOARD["RIGHT"], (5, 17))
        self.assertEqual(STANDARD_KEYBOARD["KPENTER"], (4, 21))


if __name__ == "__main__":
    unittest.main()
