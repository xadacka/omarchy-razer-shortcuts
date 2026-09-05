#!/bin/bash

set -euo pipefail

ASSUME_YES=0
OPENRAZER_COMMIT="1045a95323314b1403be4cd5849ac51fcac638ea"
AUR_COMMIT="09ec9629657898567183b51f5b57103dcdda19f9"
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

has_blade_16_2026() {
  for product_file in /sys/bus/usb/devices/*/idProduct; do
    [[ -r $product_file ]] || continue
    product=$(<"$product_file")
    vendor_file="${product_file%/idProduct}/idVendor"
    [[ -r $vendor_file ]] || continue
    vendor=$(<"$vendor_file")
    [[ ${vendor,,} == 1532 && ${product,,} == 02e0 ]] && return 0
  done
  return 1
}

install_patched_openrazer() {
  echo
  echo "The Razer Blade 16 (2026), USB 1532:02e0, is awaiting upstream support."
  echo "This builds tracked Arch -git packages from Florian's open OpenRazer PR:"
  echo "  https://github.com/openrazer/openrazer/pull/2894"
  echo "Pinned OpenRazer commit: $OPENRAZER_COMMIT"
  confirm "Build and install the pinned Blade 16 (2026) OpenRazer packages?" || return 1

  if [[ ! -e /usr/lib/modules/$(uname -r)/build ]]; then
    echo "Kernel headers for $(uname -r) are missing." >&2
    echo "Install the matching headers package, reboot if needed, and rerun setup." >&2
    return 1
  fi

  omarchy pkg add base-devel git
  build_root=$(mktemp -d)
  trap 'rm -rf -- "$build_root"' RETURN
  git clone https://aur.archlinux.org/openrazer-git.git "$build_root/openrazer-git"
  git -C "$build_root/openrazer-git" checkout --detach "$AUR_COMMIT"
  sed -i \
    "s|git+https://github.com/openrazer/openrazer.git|git+https://github.com/xadacka/openrazer.git#commit=$OPENRAZER_COMMIT|" \
    "$build_root/openrazer-git/PKGBUILD"
  (
    cd "$build_root/openrazer-git"
    PATH=/usr/bin:/bin makepkg -sC --noconfirm
  )
  shopt -s nullglob
  packages=("$build_root/openrazer-git"/*.pkg.tar.zst)
  shopt -u nullglob
  (( ${#packages[@]} )) || { echo "OpenRazer package build produced no packages." >&2; return 1; }
  if (( ASSUME_YES )); then
    sudo pacman -U --needed --noconfirm "${packages[@]}"
  else
    sudo pacman -U --needed "${packages[@]}"
  fi
  echo "✓ Installed OpenRazer from pinned Blade-support commit"
  echo "Reboot after setup so razerkbd binds to the laptop at boot."
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

if has_blade_16_2026 && ! pacman -Q openrazer-driver-dkms-git >/dev/null 2>&1; then
  install_patched_openrazer
fi

permission_group="openrazer"
getent group "$permission_group" >/dev/null || permission_group="plugdev"
if ! id -nG "$USER" | tr ' ' '\n' | grep -qx "$permission_group"; then
  echo
  echo "Your user is not listed in the $permission_group group."
  if confirm "Add '$USER' to the $permission_group group? (sudo; requires logout/login)"; then
    sudo gpasswd -a "$USER" "$permission_group"
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

theme_hook_name="theme-set-reload-razer-shortcuts.sh"
theme_hook_dest="$HOME/.config/omarchy/hooks/theme-set.d/$theme_hook_name"
if [[ -f $theme_hook_dest ]]; then
  echo "✓ Instant theme-change reload hook already installed"
elif confirm "Install a theme-set hook so switching themes reloads keyboard colors instantly (instead of within themeRefreshSec)?"; then
  omarchy hook install theme-set "$plugin_dir/hooks/$theme_hook_name"
else
  echo "Skipped; the daemon still picks up theme changes on its own within themeRefreshSec."
fi

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
