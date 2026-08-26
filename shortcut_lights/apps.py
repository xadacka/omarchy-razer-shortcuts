"""Application-aware shortcut layers."""

from __future__ import annotations


CHROMIUM_CLASSES = (
    "chromium", "google-chrome", "brave-browser", "brave", "microsoft-edge",
    "microsoft-edge-dev", "microsoft-edge-beta", "vivaldi", "vivaldi-stable",
)

# Shared Chromium-family Linux shortcuts. These intentionally describe keys,
# not actions: the keyboard is a glanceable map rather than a help overlay.
CHROMIUM_SHORTCUTS: dict[int, set[str]] = {
    4: {
        "A", "C", "D", "E", "F", "G", "H", "J", "K", "L", "N", "O",
        "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "EQUAL", "MINUS", "RETURN", "TAB", "PAGEUP", "PAGEDOWN", "F4",
    },
    5: {
        "A", "B", "D", "G", "I", "J", "K", "L", "M", "N", "O", "P",
        "R", "T", "U", "V", "W", "DELETE", "RETURN", "TAB",
    },
    8: {"LEFT", "RIGHT", "HOME", "F4", "E", "F"},
    9: {"B", "I", "T"},
}


def application_targets(window_class: str, modifier_mask: int) -> set[str]:
    app = window_class.strip().lower()
    if any(name in app for name in CHROMIUM_CLASSES):
        return set(CHROMIUM_SHORTCUTS.get(modifier_mask, set()))
    return set()
