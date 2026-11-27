#!/usr/bin/env bash
# Renders the app icons a phone uses when Cuisine is installed from
# public/favicon.svg, with ImageMagick. Run it again after changing the
# favicon and commit the PNGs it writes to public/icons/.
#
# The "any" icons keep the favicon's rounded corners. The maskable icon and
# the Apple touch icon fill the whole square, because Android and iOS cut
# their own shape out of it; the glyph already sits inside the safe zone.
set -euo pipefail

cd "$(dirname "$0")/.."
src=public/favicon.svg
out=public/icons
mkdir -p "$out"

square=$(mktemp --suffix=.svg)
trap 'rm -f "$square"' EXIT
sed 's/ rx="[0-9.]*"//' "$src" > "$square"

render() {
  convert -background none -density 1200 "$1" -resize "$2x$2" -strip "PNG32:$3"
}

render "$src" 192 "$out/icon-192.png"
render "$src" 512 "$out/icon-512.png"
render "$square" 512 "$out/icon-maskable-512.png"
render "$square" 180 "$out/apple-touch-icon.png"
