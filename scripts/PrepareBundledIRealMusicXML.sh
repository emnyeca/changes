#!/usr/bin/env bash

# Stage the bundled ireal-musicxml converter and a native macOS Node.js
# runtime for the desktop build.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "FAIL: this staging script must run on macOS" >&2
    exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
ireal_version="${IREAL_MUSICXML_VERSION:-2.1.1}"
node_version="${NODE_VERSION:-22.14.0}"

case "$(uname -m)" in
    arm64) node_arch="arm64" ;;
    x86_64) node_arch="x64" ;;
    *)
        echo "FAIL: unsupported macOS architecture: $(uname -m)" >&2
        exit 1
        ;;
esac

ireal_dir="$repo_root/tools/bundled/ireal-musicxml"
node_dir="$repo_root/tools/bundled/node"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/eub-changes-build.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

mkdir -p "$ireal_dir/build" "$node_dir"

ireal_tarball="$work_dir/ireal-musicxml.tgz"
ireal_url="https://registry.npmjs.org/@music-i18n/ireal-musicxml/-/ireal-musicxml-${ireal_version}.tgz"
echo "Downloading ireal-musicxml ${ireal_version}"
curl --fail --location --silent --show-error "$ireal_url" --output "$ireal_tarball"
mkdir -p "$work_dir/ireal"
tar -xzf "$ireal_tarball" -C "$work_dir/ireal"
cp "$work_dir/ireal/package/build/ireal-musicxml.mjs" "$ireal_dir/build/"
cp "$work_dir/ireal/package/LICENSE.txt" "$ireal_dir/"
cp "$work_dir/ireal/package/package.json" "$ireal_dir/"

node_archive_name="node-v${node_version}-darwin-${node_arch}"
node_archive="$work_dir/${node_archive_name}.tar.gz"
node_url="https://nodejs.org/dist/v${node_version}/${node_archive_name}.tar.gz"
echo "Downloading Node.js ${node_version} for macOS ${node_arch}"
curl --fail --location --silent --show-error "$node_url" --output "$node_archive"
mkdir -p "$work_dir/node"
tar -xzf "$node_archive" -C "$work_dir/node"
cp "$work_dir/node/$node_archive_name/bin/node" "$node_dir/node"
cp "$work_dir/node/$node_archive_name/LICENSE" "$node_dir/LICENSE"
chmod 755 "$node_dir/node"

echo "OK: macOS build tools staged"
