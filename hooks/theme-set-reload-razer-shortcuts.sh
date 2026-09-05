#!/bin/bash
# Omarchy theme-set hook: reload Razer Shortcut Lights the instant a theme is
# applied, instead of waiting for its periodic themeRefreshSec poll.
#
# Installed via `omarchy hook install theme-set <this file>` (setup.sh offers
# this). Fires after Omarchy has finished writing the new theme's files, so
# colors.toml is already current when this runs.
#
# Best-effort and silent: if the shell isn't Quickshell-based, the plugin is
# disabled, or the IPC call otherwise fails, this just no-ops — the daemon's
# own polling still catches the change within themeRefreshSec regardless.

qs -n -p /usr/share/omarchy/shell ipc call razer-shortcuts reload >/dev/null 2>&1 || true
