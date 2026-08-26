"""Pure binding parsing and lighting selection logic."""

from __future__ import annotations

import re

from .layouts import MODIFIER_BITS, normalize_key


ARROW = "→"


def parse_binding_lines(output: str) -> dict[int, set[str]]:
    """Parse `omarchy menu keybindings --print` into modmask -> target keys."""
    bindings: dict[int, set[str]] = {}
    for line in output.splitlines():
        combo = line.split(ARROW, 1)[0].strip()
        if not combo:
            continue
        # Omarchy formats this as `SUPER SHIFT + F`: modifiers are a
        # whitespace-separated group and the final key follows the plus.
        groups = [part.strip().upper() for part in re.split(r"\s+\+\s+", combo)]
        if not groups:
            continue
        parts = groups[:-1] + groups[-1].split()
        if len(groups) > 1:
            parts = " ".join(groups[:-1]).split() + [groups[-1]]
        mask = 0
        target = ""
        for part in parts:
            canonical_modifier = "CTRL" if part == "CONTROL" else part
            if canonical_modifier in MODIFIER_BITS:
                mask |= MODIFIER_BITS[canonical_modifier]
            else:
                target = normalize_key(part)
        if mask and target and not target.startswith(("XF86", "MOUSE:", "MOUSE_", "SWITCH:")):
            bindings.setdefault(mask, set()).add(target)
    return bindings


def active_targets(bindings: dict[int, set[str]], held_mask: int) -> set[str]:
    """Return only shortcuts whose modifier set exactly matches held modifiers."""
    return set(bindings.get(held_mask, set()))
