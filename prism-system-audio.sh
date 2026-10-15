#!/usr/bin/env bash
# PRISM v4 — "PRISM System Audio" input device.
#
# Brave/Chromium hide PulseAudio/PipeWire ".monitor" sources from web pages,
# and on Linux their screen-share picker only offers tab audio. So the page
# cannot hear system audio on its own. This runs a PipeWire loopback that
# records whatever plays on the default output and presents it as an ordinary
# input device named "PRISM System Audio", which the page picks up by name.
#
# It runs as a transient systemd --user unit: gone after logout/reboot, never
# becomes the default mic (the configured default source is left alone).
#
#   prism-system-audio.sh           start it if it is not already running
#   prism-system-audio.sh stop      remove the device
#   prism-system-audio.sh status    print whether the device exists
set -u
UNIT=prism-system-audio
NODE=prism_system_audio

have_node() { pactl list short sources 2>/dev/null | awk -v n="$NODE" '$2 == n { f = 1 } END { exit !f }'; }

case "${1:-start}" in
  stop)
    systemctl --user stop "$UNIT" 2>/dev/null
    exit 0 ;;
  status)
    if have_node; then echo "PRISM System Audio: present"; else echo "PRISM System Audio: absent"; exit 1; fi
    exit 0 ;;
  start) ;;
  *) echo "usage: $0 [start|stop|status]" >&2; exit 2 ;;
esac

have_node && exit 0
# a stale/failed unit of the same name would block systemd-run
systemctl --user stop "$UNIT" 2>/dev/null
systemctl --user reset-failed "$UNIT" 2>/dev/null

# Capture side: no node.target, so it follows the default output's monitor.
systemd-run --user --unit="$UNIT" --collect --quiet \
  pw-loopback \
    --capture-props='stream.capture.sink=true node.name=prism_system_audio_capture node.description="PRISM loopback capture"' \
    --playback-props='media.class=Audio/Source node.name=prism_system_audio node.description="PRISM System Audio"' \
  || exit 1

for _ in $(seq 20); do have_node && exit 0; sleep 0.1; done
echo "prism-system-audio: device did not appear (see: journalctl --user -u $UNIT)" >&2
exit 1
