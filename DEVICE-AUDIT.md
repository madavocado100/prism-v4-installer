# Device-selection audit

The initial defects below were reproduced against the original code before
implementing the fix in this separate edition.

| Defect | Effect | Regression coverage |
| --- | --- | --- |
| Missing remembered mic resolves to `default` | Unexpected input captured after a device disappears | `tests/devices.cjs`: missing microphone |
| Stop leaves pending request valid | A late permission response restarts capture | `tests/devices.cjs`: stop pending permission |
| Enumeration results have no ordering guard | Old scan replaces the current device list | `tests/devices.cjs`: newest device scan |
| System audio requires a loopback on every OS | Windows native desktop-audio capture is never offered | `tests/devices.cjs`: Windows desktop capture |
| Loopbacks hidden from individual selection | User cannot select a second loopback or remember it | `tests/devices.cjs`: loopback selection |
| Generic sharing options | Browser may move focus and offer tab-switch highlighting | `tests/capture.cjs`: focus and surface-switching options |
| Silent screen share only reports an error | Linux desktop audio does not start | `tests/capture.cjs`: loopback fallback |

The local desktop shortcut also bypassed `prism-v4.sh`, so no desktop-audio
input was created on launch. The new installer creates separate shortcuts
that call the launcher. The original local shortcut has been left untouched.

Tests use real browser audio graphs with controlled media-device responses
for cancellation, ordering and Windows capture cases. Windows shortcut creation
and browser regressions run in Windows CI. A manual Windows system-audio picker
session remains a separate hardware/UI acceptance check. Browser-owned capture
indicators remain controlled by the browser.

## Linux native capture update

The installed Linux launcher now uses a native local PCM host rather than the
older virtual-microphone helper. Tests on the local PipeWire server established
nonzero desktop signal and app isolation using two independent tones on a
temporary output. Default microphone/output values remained unchanged. The
included signal amplitude was 0.2441 and excluded signal amplitude 0.000176.
The test removed its temporary players and sink afterward.

Whole-desktop capture records final physical monitors once; it no longer follows
only one default output. Exclusions use application identity and all matching
playback streams rather than process IDs. Virtual forwarding is traced so an
echo-cancellation playback bus is not counted twice, and private microphone
buses are not mistaken for desktop sound. A selected output disappearing stops
its old capture and reports an error. See [LINUX-AUDIO.md](LINUX-AUDIO.md).

Native API and browser tests cover authorization, actual PCM reaching the
analyser, output/app selection, capture stop, and cancelling wallpaper permission.
Installer tests cover isolated install/update/uninstall and removal of an owned
startup entry even when the host is offline. Live X11 preview verified desktop
bounds and placement beneath desktop icons without creating a startup entry.

These checks do not exhaust every audio server or custom forwarding topology.
Per-app exclusions require per-stream monitor support. Wayland live wallpaper
is not supported. Device-label recovery in standalone browser capture may still
be ambiguous when two inputs have identical labels; select an input explicitly.
