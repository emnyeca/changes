#!/usr/bin/env bash

# Build an unsigned EUB Changes.app for the current macOS architecture.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "FAIL: the macOS desktop app must be built on macOS" >&2
    exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
cd "$repo_root"

python -m pip install -e ".[ui,midi,realtime,sysex,desktop]"

if [[ ! -f "tools/bundled/ireal-musicxml/build/ireal-musicxml.mjs" || ! -x "tools/bundled/node/node" ]]; then
    "$script_dir/PrepareBundledIRealMusicXML.sh"
fi

python scripts/verify_desktop_build.py

iconset_dir="build/macos/EUBChanges.iconset"
icon_path="build/macos/EUBChanges.icns"
icon_source="docs/assets/1x/eub_changes_logo_square.png"
mkdir -p "$iconset_dir"

while read -r size filename; do
    sips -z "$size" "$size" "$icon_source" --out "$iconset_dir/$filename" >/dev/null
done <<'SIZES'
16 icon_16x16.png
32 icon_16x16@2x.png
32 icon_32x32.png
64 icon_32x32@2x.png
128 icon_128x128.png
256 icon_128x128@2x.png
256 icon_256x256.png
512 icon_256x256@2x.png
512 icon_512x512.png
1024 icon_512x512@2x.png
SIZES

iconutil -c icns "$iconset_dir" -o "$icon_path"

streamlit-desktop-app build src/changes/main_ui.py \
  --name "EUB Changes" \
  --icon "$icon_path" \
  --streamlit-options \
    --theme.base=light \
    --theme.primaryColor="#7E5CC6" \
    --theme.backgroundColor="#FBF7FC" \
    --theme.secondaryBackgroundColor="#F4EEF8" \
    --theme.textColor="#191326" \
    --client.toolbarMode=viewer \
  --pyinstaller-options \
    --onefile \
    --windowed \
    --clean \
    --collect-all changes \
    --collect-all digitone_syx_toolkit \
    --copy-metadata digitone-syx-toolkit \
    --collect-all mido \
    --collect-all rtmidi \
    --hidden-import mido.backends.rtmidi \
    --hidden-import rtmidi \
    --add-data "docs/assets/1x:docs/assets/1x" \
    --add-data "LICENSE:." \
    --add-data "THIRD_PARTY_NOTICES.md:." \
    --add-data "tools/eub-ireal-wrapper.mjs:tools" \
    --add-data "tools/bundled/ireal-musicxml:tools/bundled/ireal-musicxml" \
    --add-data "tools/bundled/node:tools/bundled/node" \
    --noconfirm

app_path="dist/EUB Changes.app"
if [[ ! -d "$app_path" ]]; then
    echo "FAIL: expected app bundle was not created: $app_path" >&2
    exit 1
fi

codesign --verify --deep --strict "$app_path"
echo "OK: $app_path"
