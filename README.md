# Razer Shortcut Lights for Omarchy

The one-stop lighting daemon for a Razer keyboard on Omarchy: it keeps the
whole board synced to your current Omarchy theme's actual color palette — an
ambient, full-keyboard random sparkle animation at rest, vivid theme-derived
colors — and turns it into a live shortcut map the instant you hold a
modifier, showing only the keys that complete shortcuts for that exact
combination.

![Omarchy](https://img.shields.io/badge/Omarchy-Quattro-111827)
![OpenRazer](https://img.shields.io/badge/OpenRazer-3.x-00ff66)
![License](https://img.shields.io/badge/license-MIT-blue)

## What it does

**Theme-synced ambient lighting (resting state)**

- Reads your active Omarchy theme's `colors.toml` and picks its vibrant colors,
  filtering out near-black/near-white ones so the board never looks washed out.
  Works regardless of the theme's naming convention — some themes use
  `color0`-`color15`, others name channels directly (`red`/`cyan`/`bright_blue`/
  etc.) — every hex value in the file is a candidate; nothing is tied to a
  specific key name, so no color is ever hardcoded to a particular hue
- Default resting mode is `sparkle`: every key is always a bright, solid,
  high-saturation color — drawn from *that specific theme's* two most intense
  colors (highest chroma, whatever they happen to be — cyan and magenta only
  if your theme's most saturated colors genuinely are cyan and magenta),
  slowly crossfading between them if there's more than one — while random keys
  across the whole board twinkle on top in the theme's other colors, fading in
  and out independently and continuously; no plain breathe/fade, and resting
  keys are never black
- Sparkles that happen to land on one of those same intense colors "stick" —
  holding at full brightness for tens of seconds instead of a fraction of one
  — so the board slowly accumulates a scattering of long-lived vivid
  highlights alongside the quicker, more varied twinkle of the rest
- Reacts to theme changes instantly if you install the optional `theme-set`
  hook (setup offers this — see [Instant theme-change reload](#instant-theme-change-reload)
  below); otherwise it still picks up changes live via a periodic poll
  (`themeRefreshSec`, default every 5s), no restart needed either way
- Alternate resting modes: flat `static` theme color, or the original
  `previousEffect` behavior (restore whichever native OpenRazer effect — Spectrum,
  Wave, Breathing, etc. — was active before the daemon started painting)

**Shortcut overlay (while a modifier is held)**

- Reads the shortcuts shown by `omarchy menu keybindings --print`
- Refreshes automatically when Omarchy or personal bindings change
- Shows exact layers: `Super+Shift` displays only `Super+Shift` shortcuts
- Color-codes Super, Shift, Ctrl, Alt, and their combinations — by default,
  every one of these 13 layer colors and 4 modifier-key colors is itself
  derived from your theme's most intense colors (same chroma ranking as the
  sparkle base, just a wider slice of it — `modifierIntenseCount` colors
  instead of `sparkleSignatureCount`), deterministically, so it's stable
  across restarts, not hardcoded
- Turns bare Shift into a full-keyboard inverse-color layer
- Shows Chromium-family shortcuts when Chrome, Chromium, Brave, Edge, or
  Vivaldi is focused
- Listens only for modifier transitions; it never grabs or records normal keys

Any of `activeColor`, `modifierColor`, `layerColors`, or `modifierKeyColors`
set explicitly in your config file overrides the theme for that setting —
theme-sync only fills in what you haven't customized.

## Compatibility

The plugin supports OpenRazer keyboards that use its standard sparse keyboard
matrix, from compact laptop layouts through full-size boards with numpads. It
clips the canonical `6×22` key coordinates to each device's reported matrix.
Nonstandard keypads such as Tartarus and Orbweaver need their own adapter and
currently fail safely instead of lighting the wrong controls.

The Razer Blade 16 (2026), USB ID `1532:02e0`, is supported by
[OpenRazer PR #2894](https://github.com/openrazer/openrazer/pull/2894) but is not
in OpenRazer 3.12.4. On that laptop, setup offers to build proper Arch `-git`
packages from the exact tested commit in
[`xadacka/openrazer`](https://github.com/xadacka/openrazer/tree/blade-16-2026-support).
The source commit is pinned rather than following a moving branch. Once support
lands in an OpenRazer release, this temporary path can be removed.

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
user to the permission group when needed. On a Blade 16 (2026), it detects USB
ID `1532:02e0` and offers the pinned PR build described above. The build uses a
pinned AUR packaging revision and produces packages tracked by pacman; it does
not overwrite package-owned files by hand. Nothing is installed silently.

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
[`config.example.json`](config.example.json) for the sparkle/theme tunables,
or the table below for every setting (including the color overrides it omits
by default so theme-sync stays in control).

| Setting | Default | Meaning |
| --- | --- | --- |
| `activeColor` | Theme's most intense color | Base shortcut color and Shift inversion source |
| `modifierColor` | Theme-derived (intense) | Fallback held-modifier color |
| `layerColors` | Theme-derived (intense) | Target color for each exact modifier set |
| `modifierKeyColors` | Theme-derived (intense) | Individual modifier colors |
| `shiftAloneMode` | `invert` | Bare Shift behavior |
| `applicationShortcuts` | `true` | Add shortcuts for the focused supported app |
| `includeModifierKeys` | `true` | Illuminate held modifier keys |
| `refreshBindingsSec` | `10` | Binding refresh interval while idle |
| `deviceSerial` | `auto` | Select a particular OpenRazer device |
| `modifierIntenseCount` | `8` | How many of the theme's most saturated colors `activeColor`/`modifierColor`/`layerColors`/`modifierKeyColors` are derived from |
| `restingMode` | `sparkle` | `sparkle` (ambient twinkle), `static` (flat theme color), or `previousEffect` (restore prior native effect) |
| `sparkleFps` | `24` | Animation frame rate while idle |
| `sparkleSpawnRate` | `4.0` | New sparkles spawned per second, board-wide |
| `sparkleMaxConcurrent` | `null` (auto) | Cap on simultaneous sparkles; auto-scales to keyboard size |
| `sparkleBrightness` | `100` | Peak brightness (%) of each sparkle at its hold phase |
| `sparkleSignatureCount` | `2` | How many of the theme's most saturated colors the base layer cycles through, and which sparkle colors "stick" |
| `sparkleBaseBrightness` | `90` | Brightness (%) of the solid signature-color base — bright and high-saturation; resting keys are never black |
| `sparkleBaseCycleSec` | `20.0` | Seconds on each signature color before crossfading to the next (only matters when `sparkleSignatureCount` > 1) |
| `sparkleStickyMinSec` / `sparkleStickyMaxSec` | `20.0` / `60.0` | Hold-time range (seconds) for a sparkle that lands on a signature color, before it fades out like any other |
| `themeRefreshSec` | `5` | How often to check for a theme change while running |

Any of `activeColor`, `modifierColor`, `layerColors`, or `modifierKeyColors` set
explicitly in your config file is never overwritten by the theme, live or
otherwise — theme-sync only fills in the ones you leave unset.

After changing config, disable and re-enable the plugin:

```bash
omarchy plugin disable io.github.xadacka.razer-shortcuts
omarchy plugin enable io.github.xadacka.razer-shortcuts
```

## Instant theme-change reload

By default, switching Omarchy themes is picked up within `themeRefreshSec`
(5s) via a background poll. `setup.sh` also offers to install an Omarchy
`theme-set` hook (see `omarchy help hook`, or `~/.config/omarchy/hooks/` —
scripts in `theme-set.d/` run after a theme is applied) that reloads the
daemon the instant `omarchy theme set` finishes, instead of waiting for the
next poll:

```bash
omarchy hook install theme-set ~/.config/omarchy/plugins/io.github.xadacka.razer-shortcuts/hooks/theme-set-reload-razer-shortcuts.sh
```

The hook just calls the same IPC reload `Service.qml` already exposes:

```bash
qs -n -p /usr/share/omarchy/shell ipc call razer-shortcuts reload
```

It's best-effort and silent — if the shell isn't running, the plugin is
disabled, or the IPC call otherwise fails, it no-ops, and the periodic poll
still catches the change regardless. Uninstall by deleting
`~/.config/omarchy/hooks/theme-set.d/theme-set-reload-razer-shortcuts.sh`.

If you have other scripts in `~/.config/omarchy/hooks/theme-set.d/` that also
touch this keyboard's lighting (a leftover one-off `fx.static()` script, an
OpenRGB sync script, etc.), they'll race this daemon on every theme switch —
worth checking that directory for anything redundant.

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

While idle, it redraws the advanced per-key matrix itself at `sparkleFps`
(default 24) to animate the sparkle effect, or sends one draw whenever the
theme changes (`static` mode) or a modifier is pressed or released (shortcut
overlay). In `previousEffect` mode it falls back to the original behavior:
since OpenRazer cannot read back a custom advanced per-key framebuffer, only
named effects and their reported colors can be restored, not an arbitrary
advanced matrix — so the service re-reads the keyboard's current effect and
colors at the start of every press rather than once at launch, so a theme
change or other lighting update made while it was already running is never
invisible to it.

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
`~/.config/omarchy/razer-shortcuts.json` until you remove it, and so does the
theme-set hook, if installed, at
`~/.config/omarchy/hooks/theme-set.d/theme-set-reload-razer-shortcuts.sh` —
delete it manually if you're removing the plugin for good.

## Development

```bash
omarchy plugin validate .
python3 -m unittest discover tests -v
python3 daemon.py doctor
```

The repository root is the installable plugin—there is no generated bundle and
no install hook. Contributions for tested nonstandard keyboard/keypad matrix
adapters are welcome.

## License

[MIT](LICENSE). This is an unofficial community plugin and is not affiliated
with Razer, OpenRazer, or Omarchy.
