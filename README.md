# Razer Shortcut Lights for Omarchy

An Omarchy service plugin that turns a supported OpenRazer keyboard into a
live shortcut guide. Hold `Super`, `Alt`, `Ctrl`, `Shift`, or a combination and
only keys that complete a currently mapped Omarchy/Hyprland shortcut light up.

Shortcut layers are color-coded by modifier: Super is cyan, Alt magenta, Ctrl
amber, and combinations get distinct contrasting colors. Holding Shift by
itself turns the whole physical key map into the inverse of `activeColor`, so
Shift remains a useful visual layer even when it has no standalone shortcuts.

The plugin reads the same list shown by `omarchy menu keybindings --print`, so
it follows Omarchy updates and personal bindings automatically. Modifier sets
match exactly: holding `Super+Shift` shows `Super+Shift` shortcuts, not the
larger set of shortcuts bound to `Super` alone.

## Requirements

- Omarchy 4 with shell plugin support
- OpenRazer daemon and Python client (`openrazer-daemon`, `python-openrazer`)
- A per-key OpenRazer keyboard
- Permission to read the keyboard event device (OpenRazer's Arch package sets
  the device group to `openrazer`)

The first hardware adapter is for the Razer Blade 16 (2025/2026), whose
OpenRazer matrix is `6×17`.

## Install

```bash
omarchy plugin add https://github.com/YOUR_USER/omarchy-razer-shortcuts.git --enable
```

For local development:

```bash
omarchy plugin validate .
python3 -m unittest discover tests
python3 daemon.py doctor
```

Then add the local Git checkout with `omarchy plugin add file:///absolute/path
--enable`, or copy it to
`~/.config/omarchy/plugins/io.github.florian.razer-shortcuts` and run:

```bash
omarchy plugin enable io.github.florian.razer-shortcuts
```

## Configuration

The defaults require no config. To create an editable user config:

```bash
python3 daemon.py init-config
```

This writes `~/.config/omarchy/razer-shortcuts.json`. Restart just this service
after editing it:

```bash
omarchy-shell ipc call razer-shortcuts reload
```

Available settings:

| Setting | Default | Meaning |
| --- | --- | --- |
| `activeColor` | `#38bdf8` | Available shortcut target keys |
| `modifierColor` | `#ffffff` | Held modifier keys |
| `layerColors` | modifier palette | Target color for each exact modifier set |
| `modifierKeyColors` | cyan/orange/amber/magenta | Individual held-modifier colors |
| `shiftAloneMode` | `invert` | Invert `activeColor` across all keys for bare Shift |
| `includeModifierKeys` | `true` | Also illuminate held modifiers |
| `refreshBindingsSec` | `10` | Refresh bindings while idle |
| `deviceSerial` | `auto` | Select a specific OpenRazer serial |

## How it works

The service opens the Razer keyboard event stream read-only. It listens only
for modifier key press/release events; it does not grab the device, inject
input, or record ordinary keystrokes. On a modifier change it performs one
OpenRazer matrix draw. On release it restores the prior named lighting effect.

OpenRazer cannot read back a keyboard's current advanced per-key framebuffer.
Named effects and their reported colors are restored; a custom advanced matrix
cannot be reconstructed after an overlay.

## Troubleshooting

```bash
python3 daemon.py doctor
journalctl --user -u openrazer-daemon
```

If `doctor` reports that the event device is not readable, ensure the user is
in the `openrazer` group and log out/in. The plugin never runs as root.

## Security

Omarchy shell plugins execute as the logged-in user. Review plugins before
enabling them. This plugin launches one local Python process, opens only
Razer-labelled keyboard event nodes, and connects to the existing OpenRazer
user daemon over D-Bus.
