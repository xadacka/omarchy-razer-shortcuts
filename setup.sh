#!/bin/bash

set -euo pipefail

ASSUME_YES=0
if [[ ${1:-} == "--yes" || ${1:-} == "-y" ]]; then
  ASSUME_YES=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--yes]" >&2
  exit 2
fi

confirm() {
  local prompt="$1"
  (( ASSUME_YES )) && return 0
  if command -v gum >/dev/null 2>&1; then
    gum confirm "$prompt"
  else
    read -r -p "$prompt [y/N] " answer
    [[ $answer == [yY] || $answer == [yY][eE][sS] ]]
  fi
}

echo "Razer Shortcut Lights setup"
echo

missing=()
for package in openrazer-daemon python-openrazer; do
  pacman -Q "$package" >/dev/null 2>&1 || missing+=("$package")
done

if (( ${#missing[@]} )); then
  echo "Missing required packages: ${missing[*]}"
  echo "OpenRazer installs a DKMS kernel driver and a per-user D-Bus daemon."
  if confirm "Install the missing OpenRazer packages with 'omarchy pkg add'?"; then
    omarchy pkg add "${missing[@]}"
  else
    echo "Nothing installed. Run this setup again when ready."
    exit 1
  fi
else
  echo "✓ OpenRazer packages are installed"
fi

if ! id -nG "$USER" | tr ' ' '\n' | grep -qx openrazer; then
  echo
  echo "Your user is not listed in the openrazer group."
  if confirm "Add '$USER' to the openrazer group? (sudo; requires logout/login)"; then
    sudo gpasswd -a "$USER" openrazer
    echo "Log out and back in after setup so the new group membership applies."
  else
    echo "Skipped group membership; keyboard event permissions may prevent the plugin from working."
  fi
else
  echo "✓ User is in the openrazer group"
fi

systemctl --user enable --now openrazer-daemon.service
echo "✓ OpenRazer daemon enabled and started"

plugin_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if python3 "$plugin_dir/daemon.py" doctor; then
  echo
  echo "✓ Razer Shortcut Lights is ready"
else
  echo
  echo "Setup completed, but the doctor still found a problem."
  echo "If group membership changed, log out and back in, then run:"
  echo "  $plugin_dir/setup.sh"
  exit 1
fi
