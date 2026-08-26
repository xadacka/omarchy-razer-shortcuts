# Razer Shortcut Lights for Omarchy

Turn your Razer keyboard into a live shortcut map for Omarchy. Hold a modifier
and only the keys that complete shortcuts for that exact combination light up.

![Omarchy](https://img.shields.io/badge/Omarchy-Quattro-111827)
![OpenRazer](https://img.shields.io/badge/OpenRazer-3.x-00ff66)
![License](https://img.shields.io/badge/license-MIT-blue)

## What it does

- Reads the shortcuts shown by `omarchy menu keybindings --print`
- Refreshes automatically when Omarchy or personal bindings change
- Shows exact layers: `Super+Shift` displays only `Super+Shift` shortcuts
- Color-codes Super, Shift, Ctrl, Alt, and their combinations
- Turns bare Shift into a full-keyboard inverse-color layer
- Restores the previous named OpenRazer effect and reported colors on release
- Listens only for modifier transitions; it never grabs or records normal keys

Default colors:

| Layer | Color |
| --- | --- |
| Super | Cyan |
| Alt | Magenta |
| Ctrl | Amber |
| Super + Shift | Orange |
| Other combinations | Contrasting pink, violet, green, red, and white |
| Shift alone | Inverse of the active color across the physical key map |

## Compatibility

The initial hardware adapter supports the Razer Blade 16 (2025/2026) with
OpenRazer's `6×17` per-key matrix. Other per-key Razer models need a matrix
layout adapter; unsupported dimensions fail safely instead of lighting the
wrong keys.

Requirements:

- Omarchy 4 / Quattro shell plugin support
- OpenRazer daemon and Python client
- A supported per-key Razer keyboard

## Install

Add and enable the plugin:

```bash
omarchy plugin add https://github.com/xadacka/omarchy-razer-shortcuts.git --enable
```

Then run its interactive setup:

```bash
~/.config/omarchy/plugins/io.github.xadacka.razer-shortcuts/setup.sh
```

Setup checks OpenRazer first. If it is missing, it explains the kernel-driver
and daemon changes and offers to install `openrazer-daemon` and
`python-openrazer` through `omarchy pkg add`. It also offers to add the current
user to the `openrazer` group when needed. Nothing is installed silently.

For a fully confirmed setup on a machine you administer:

```bash
~/.config/omarchy/plugins/io.github.xadacka.razer-shortcuts/setup.sh --yes
```

The Omarchy plugin command itself intentionally never executes install hooks or
uses sudo. Keeping dependency setup explicit follows the official plugin safety
model.

## Configure colors

Defaults require no config. Create an editable config with:

```bash
python3 ~/.config/omarchy/plugins/io.github.xadacka.razer-shortcuts/daemon.py init-config
```

This writes `~/.config/omarchy/razer-shortcuts.json`. See
[`config.example.json`](config.example.json) for the full palette.

| Setting | Default | Meaning |
| --- | --- | --- |
| `activeColor` | `#38bdf8` | Base shortcut color and Shift inversion source |
| `modifierColor` | `#ffffff` | Fallback held-modifier color |
| `layerColors` | Built-in palette | Target color for each exact modifier set |
| `modifierKeyColors` | Cyan/orange/amber/magenta | Individual modifier colors |
| `shiftAloneMode` | `invert` | Bare Shift behavior |
| `includeModifierKeys` | `true` | Illuminate held modifier keys |
| `refreshBindingsSec` | `10` | Binding refresh interval while idle |
| `deviceSerial` | `auto` | Select a particular OpenRazer device |

After changing config, disable and re-enable the plugin:

```bash
omarchy plugin disable io.github.xadacka.razer-shortcuts
omarchy plugin enable io.github.xadacka.razer-shortcuts
```

## Diagnostics

```bash
python3 ~/.config/omarchy/plugins/io.github.xadacka.razer-shortcuts/daemon.py doctor
journalctl --user -u openrazer-daemon
```

The doctor verifies bindings, input permissions, the OpenRazer D-Bus service,
the detected keyboard, and matrix dimensions. If setup added group membership,
log out and back in before rerunning it.

## How it works and privacy

The headless Omarchy service starts one local Python process. It opens only
keyboard event nodes carrying a Razer USB identity and reacts only to Linux
modifier codes. It does not grab the device, inspect ordinary key events,
inject input, use the network, or run as root.

On modifier changes it sends one advanced-matrix draw through the existing
OpenRazer user daemon. OpenRazer cannot read back a custom advanced per-key
framebuffer, so named effects and their reported colors can be restored, while
an arbitrary advanced matrix cannot be reconstructed.

Like every Omarchy shell plugin, this code executes unsandboxed as your logged-in
user. Review third-party plugins before enabling them.

## Update and remove

```bash
omarchy plugin update io.github.xadacka.razer-shortcuts
omarchy plugin remove io.github.xadacka.razer-shortcuts
```

Removal stops and removes the plugin. It deliberately leaves OpenRazer installed
because other applications may use it. If you installed OpenRazer solely for
this plugin, review dependants and remove it separately:

```bash
omarchy pkg drop python-openrazer openrazer-daemon
```

Your optional color config remains at
`~/.config/omarchy/razer-shortcuts.json` until you remove it.

## Development

```bash
omarchy plugin validate .
python3 -m unittest discover tests -v
python3 daemon.py doctor
```

The repository root is the installable plugin—there is no generated bundle and
no install hook. Contributions for tested keyboard matrix adapters are welcome.

## License

[MIT](LICENSE). This is an unofficial community plugin and is not affiliated
with Razer, OpenRazer, or Omarchy.
