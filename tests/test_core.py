from __future__ import annotations

import unittest

from shortcut_lights.core import active_targets, parse_binding_lines


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


if __name__ == "__main__":
    unittest.main()
