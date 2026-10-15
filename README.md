# PRISM v4 Desktop Audio — installer edition

A separate edition of [PRISM v4](https://github.com/madavocado100/prism-v4), with
Windows/Linux per-user installers and fixes for audio-device selection.
The original app and its v4.0.0 release are unchanged. This edition has a
separate installation folder, shortcut name, and browser settings keys.
The visualizer is a self-contained HTML file with no build step. You can also
serve the extracted folder with `python3 -m http.server 8080 --bind 127.0.0.1`
and open `http://localhost:8080/rgb-audio-visualizer-v4.html`.

## Windows 10 / 11

1. Extract the complete distribution ZIP.
2. Double-click **install-windows.cmd**. It installs to
   `%LOCALAPPDATA%\PrismV4Desktop` and adds **PRISM v4 Desktop Audio** shortcuts
   to your desktop and Start menu. Administrator access is not required.
3. Open the shortcut. Brave, Chrome, or Edge must be installed; the launcher
   chooses an available Chromium browser.
4. Select **Entire desktop audio**, choose **Entire screen**, and enable the
   browser's **Share system audio** option. Approve sharing.

Windows uses the browser's native system-audio capture. Browser tab capture is
also available separately. A detected loopback input (such as Stereo Mix or
VB-Cable) can be selected individually in **C → Source**. If your browser or
Windows configuration does not offer system audio, use an available loopback
input, a local audio file, or the demo. The installer does not install drivers.

To uninstall, run `install-windows.cmd -Uninstall` from the extracted folder.
PowerShell is included with Windows; Python and Node.js are not required.
The wrapper's execution-policy option applies only to that process.

## Linux

Requires Python 3 and Bash for installation, plus Brave, Chrome, or Chromium.
For desktop audio, use a PipeWire desktop with PulseAudio compatibility,
`pw-loopback`, `pactl`, and a working `systemd --user` session. Package names
vary by distribution (commonly `pipewire-bin` and `pulseaudio-utils`).

From the extracted folder:

```sh
bash install-linux.sh
```

Open **PRISM v4 Desktop Audio** from the application menu, then choose
**Entire desktop audio** or press **A**. Grant microphone permission so the
browser can read the virtual input. The shortcut starts the audio helper
before opening the browser; no tab or screen is shared for this mode.

The app installs under `${XDG_DATA_HOME:-~/.local/share}/prism-v4-desktop` and
creates a distinct `prism-v4-desktop.desktop` entry. The helper exposes the
default output as **PRISM System Audio**, leaves your default microphone
alone, and runs until logout/reboot or until stopped:

```sh
~/.local/share/prism-v4-desktop/prism-system-audio.sh stop
```

For a non-default browser, set `PRISM_BROWSER` to its executable path before
running the launcher. The installed app is independent of the extracted
installer folder. Re-run the installer to update it.

```sh
bash install-linux.sh --uninstall
```

Both installers remove only their known payload files and shortcuts. They
preserve unrelated files in the install folder and browser settings.

## Audio selection fixes

- An unavailable remembered microphone stays visible as unavailable. Prism
  requests an explicit choice instead of silently recording the default mic.
- A stopped capture cannot be restarted by a late permission response; any
  stream returned after cancellation is immediately closed.
- A slow older device scan cannot overwrite a newer scan.
- Every detected loopback input is selectable in the Source menu. The last
  selected loopback is remembered, including when its device ID changes but
  its label stays the same.
- Windows desktop audio opens native screen-audio capture directly from the
  click. Linux uses the desktop loopback without a sharing picker.
- A Linux screen/window share with no audio falls back to the desktop input.
- Optional tab sharing requests no focus change, excludes Prism itself, and
  requests removal of “Share this tab instead”. Browser capture indicators
  remain controlled by the browser.

See [DEVICE-AUDIT.md](DEVICE-AUDIT.md) for verification details and limits.

## Defaults and controls

All 101 original fresh-start defaults are preserved in
[`config/default.json`](config/default.json). Load it with **C → Load settings**
or drop it onto the app. Settings for this edition use `prism.v4.desktop.*`
keys; original Prism settings are not imported automatically.

A fresh launch is labelled Hyperdrive with `orbitSpeed: 1`; Reset reapplies
the original Hyperdrive preset with `orbitSpeed: 0.9`. This existing distinction
is preserved.

| Key | Action |
| --- | --- |
| D | Demo |
| M / A / T | Microphone / desktop audio / browser tab audio |
| C / Esc | Open / close settings |
| H | Toggle HUD |
| N / P | Next / previous preset |
| R | Randomise |
| F | Fullscreen |
| S | Save PNG |
| 0 | Toggle playback monitoring |

Drop an audio file onto the window to play it. Microphone and desktop inputs
are never routed back to the speakers, preventing feedback. Demo and file
playback use the monitoring volume. Append `?auto=demo&mute=1` or
`?auto=test&mute=1` to the HTML URL for demo or synthetic spectrum checks.

## Developer checks

```sh
node scripts/check.cjs
python3 tests/desktop.py
pwsh -NoProfile -File tests/windows.ps1
npm install --no-save playwright@1.62.1
npx playwright install chromium
node tests/capture.cjs
node tests/devices.cjs
```

The Windows test checks real shortcut creation when run on Windows; on Linux
it checks PowerShell parsing and the payload installation/update/uninstall
path. GitHub Actions runs the suite on both Windows and Linux.

Browser device regressions serve the app on localhost with visual layers
disabled to isolate audio routing; the default configuration and full renderer
are checked separately.
