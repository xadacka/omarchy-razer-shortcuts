"""OpenRazer's standard sparse keyboard LED-matrix layout."""

from __future__ import annotations


STANDARD_KEYBOARD: dict[str, tuple[int, int]] = {
    "ESCAPE": (0, 1),
    "F1": (0, 3), "F2": (0, 4), "F3": (0, 5), "F4": (0, 6),
    "F5": (0, 7), "F6": (0, 8), "F7": (0, 9), "F8": (0, 10),
    "F9": (0, 11), "F10": (0, 12), "F11": (0, 13), "F12": (0, 14),
    "PRINT": (0, 15), "SCROLLLOCK": (0, 16), "PAUSE": (0, 17),
    "GRAVE": (1, 1), "1": (1, 2), "2": (1, 3), "3": (1, 4),
    "4": (1, 5), "5": (1, 6), "6": (1, 7), "7": (1, 8),
    "8": (1, 9), "9": (1, 10), "0": (1, 11), "MINUS": (1, 12),
    "EQUAL": (1, 13), "BACKSPACE": (1, 14), "INSERT": (1, 15), "HOME": (1, 16),
    "PAGEUP": (1, 17), "NUMLOCK": (1, 18), "KPSLASH": (1, 19),
    "KPASTERISK": (1, 20), "KPMINUS": (1, 21),
    "TAB": (2, 1), "Q": (2, 2), "W": (2, 3), "E": (2, 4),
    "R": (2, 5), "T": (2, 6), "Y": (2, 7), "U": (2, 8),
    "I": (2, 9), "O": (2, 10), "P": (2, 11), "BRACKETLEFT": (2, 12),
    "BRACKETRIGHT": (2, 13), "DELETE": (2, 15), "END": (2, 16),
    "PAGEDOWN": (2, 17), "KP7": (2, 18), "KP8": (2, 19),
    "KP9": (2, 20), "KPPLUS": (2, 21),
    "CAPSLOCK": (3, 1), "A": (3, 2), "S": (3, 3), "D": (3, 4),
    "F": (3, 5), "G": (3, 6), "H": (3, 7), "J": (3, 8),
    "K": (3, 9), "L": (3, 10), "SEMICOLON": (3, 11), "APOSTROPHE": (3, 12),
    "BACKSLASH": (3, 13), "RETURN": (3, 14), "KP4": (3, 18),
    "KP5": (3, 19), "KP6": (3, 20),
    "LEFTSHIFT": (4, 1), "Z": (4, 3), "X": (4, 4), "C": (4, 5),
    "V": (4, 6), "B": (4, 7), "N": (4, 8), "M": (4, 9),
    "COMMA": (4, 10), "PERIOD": (4, 11), "SLASH": (4, 12),
    "RIGHTSHIFT": (4, 14), "UP": (4, 16), "KP1": (4, 18),
    "KP2": (4, 19), "KP3": (4, 20), "KPENTER": (4, 21),
    "LEFTCTRL": (5, 1), "LEFTMETA": (5, 2), "LEFTALT": (5, 3),
    "SPACE": (5, 7), "RIGHTALT": (5, 11), "FN": (5, 12),
    "MENU": (5, 13), "RIGHTCTRL": (5, 14), "LEFT": (5, 15),
    "DOWN": (5, 16), "RIGHT": (5, 17), "KP0": (5, 19), "KPDOT": (5, 20),
}

ALIASES = {
    "ESC": "ESCAPE", "ENTER": "RETURN", "KP_ENTER": "KPENTER",
    "`": "GRAVE", "~": "GRAVE", "-": "MINUS", "=": "EQUAL",
    "[": "BRACKETLEFT", "]": "BRACKETRIGHT", "\\": "BACKSLASH",
    ";": "SEMICOLON", "'": "APOSTROPHE", ",": "COMMA", ".": "PERIOD", "/": "SLASH",
    "SUPER_L": "LEFTMETA", "SUPER_R": "LEFTMETA", "SUPER": "LEFTMETA",
    "ALT_L": "LEFTALT", "ALT_R": "RIGHTALT", "ALT": "LEFTALT",
    "CTRL_L": "LEFTCTRL", "CTRL_R": "RIGHTCTRL", "CTRL": "LEFTCTRL",
    "SHIFT_L": "LEFTSHIFT", "SHIFT_R": "RIGHTSHIFT", "SHIFT": "LEFTSHIFT",
}


def normalize_key(name: str) -> str:
    key = name.strip().upper().replace(" ", "_")
    if key.startswith("CODE:"):
        try:
            xkb = int(key.split(":", 1)[1])
        except ValueError:
            return key
        # Hyprland's code: values are XKB codes (Linux evdev code + 8).
        linux_code = xkb - 8
        key = EVENT_CODE_NAMES.get(linux_code, key)
    return ALIASES.get(key, key)


EVENT_CODE_NAMES = {
    1: "ESCAPE", 2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6",
    8: "7", 9: "8", 10: "9", 11: "0", 12: "MINUS", 13: "EQUAL",
    14: "BACKSPACE", 15: "TAB", 16: "Q", 17: "W", 18: "E", 19: "R",
    20: "T", 21: "Y", 22: "U", 23: "I", 24: "O", 25: "P",
    26: "BRACKETLEFT", 27: "BRACKETRIGHT", 28: "RETURN", 30: "A", 31: "S",
    32: "D", 33: "F", 34: "G", 35: "H", 36: "J", 37: "K", 38: "L",
    39: "SEMICOLON", 40: "APOSTROPHE", 41: "GRAVE", 43: "BACKSLASH",
    44: "Z", 45: "X", 46: "C", 47: "V", 48: "B", 49: "N", 50: "M",
    51: "COMMA", 52: "PERIOD", 53: "SLASH", 57: "SPACE",
    59: "F1", 60: "F2", 61: "F3", 62: "F4", 63: "F5", 64: "F6",
    65: "F7", 66: "F8", 67: "F9", 68: "F10", 87: "F11", 88: "F12",
    102: "HOME", 103: "UP", 105: "LEFT", 106: "RIGHT", 107: "END",
    110: "INSERT", 111: "DELETE", 119: "PAUSE", 127: "MENU", 183: "F13",
}

MODIFIER_EVENT_CODES = {
    42: "SHIFT", 54: "SHIFT", 29: "CTRL", 97: "CTRL",
    56: "ALT", 100: "ALT", 125: "SUPER", 126: "SUPER",
}

MODIFIER_BITS = {"SHIFT": 1, "CTRL": 4, "ALT": 8, "SUPER": 64}
