#!/usr/bin/env bash
set -u
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! "$here/prism-system-audio.sh"; then
  echo 'Desktop audio is unavailable; microphone, files and demo remain available.' >&2
fi
browser="${PRISM_BROWSER:-}"
if [[ -z "$browser" ]]; then
  for candidate in brave-browser brave google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then browser="$candidate"; break; fi
  done
fi
if [[ -z "$browser" ]]; then
  echo 'Install Brave, Chrome or Chromium, or set PRISM_BROWSER to its executable.' >&2
  exit 1
fi
exec "$browser" --app="file://$here/rgb-audio-visualizer-v4.html" --class=PrismV4Desktop "$@"
