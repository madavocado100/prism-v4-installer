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

Requires Python 3, Bash, Brave/Chrome/Chromium, and a PulseAudio-compatible
server (including PipeWire's PulseAudio service). Desktop capture uses `pactl`
and `parec`, usually supplied by `pulseaudio-utils`. Live wallpaper also needs
an **X11** session, `xdotool`, `xprop`, `zenity`, and the X11/XFixes libraries.
On Debian/Ubuntu/Zorin, the supporting tools are available with:

```sh
sudo apt install pulseaudio-utils xdotool x11-utils zenity
bash install-linux.sh
```

Open **PRISM v4 Desktop Audio** from the application menu, then choose
**Entire desktop audio** or press **A**. The native host reads output monitors
directly: there is no microphone permission request or screen/tab sharing picker.
In **C → Linux desktop**, choose all outputs, follow the default output, or select
an output explicitly. Check apps to exclude them from capture. App audio keeps
playing normally; exclusions affect only the visualizer.

The app installs under `${XDG_DATA_HOME:-~/.local/share}/prism-v4-desktop` and
creates a distinct `prism-v4-desktop.desktop` entry. Its private browser profiles
and native settings are under `${XDG_CONFIG_HOME:-~/.config}/prism-v4-desktop`.
Use the new **PRISM v4 Desktop Audio** shortcut: an older PRISM shortcut opening
the original HTML does not start the native host.

### Live wallpaper (Linux X11)

While PRISM is open, choose **C → Linux desktop → Set as desktop wallpaper**.
A native permission dialog asks before creating
`${XDG_CONFIG_HOME:-~/.config}/autostart/prism-v4-wallpaper.desktop`.
Approval starts a click-through wallpaper below normal windows and desktop icons,
auto-scaled to the desktop bounds. It starts again at sign-in, restores saved
visualizer/audio settings, and follows display-size changes. It uses a separate
browser window capped at 30 frames/second. Wayland is not supported yet.

**Stop wallpaper & remove startup** closes it and removes its startup entry.
You can also run the following even when the native host has stopped:

```sh
~/.local/share/prism-v4-desktop/prism-v4.sh --stop
```

Installation alone never enables wallpaper or autostart. The static desktop
wallpaper, default microphone, output selection, and other apps' routing are
preserved. For a non-default Chromium browser, set `PRISM_BROWSER` to its
executable path before running the launcher. Re-run the installer to update.

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
  click. the installed Linux edition reads native output monitors without a sharing picker.
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
python3 tests/audio-routing.py
python3 tests/native.py
python3 tests/desktop.py
pwsh -NoProfile -File tests/windows.ps1
npm install --no-save playwright@1.62.1
npx playwright install chromium
node tests/capture.cjs
node tests/devices.cjs
node tests/native-browser.cjs
# Optional live PulseAudio/PipeWire signal test (temporary null sink):
PRISM_LIVE_AUDIO_TEST=1 python3 tests/linux-signal.py
```

The Windows test checks real shortcut creation when run on Windows; on Linux
it checks PowerShell parsing and the payload installation/update/uninstall
path. GitHub Actions runs the suite on both Windows and Linux.

Browser device regressions serve the app on localhost with visual layers
disabled to isolate audio routing; the default configuration and full renderer
are checked separately.

See [LINUX-AUDIO.md](LINUX-AUDIO.md) for native routing and exclusion behavior.
