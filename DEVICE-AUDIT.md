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
for cancellation, ordering and platform cases. They do not prove a particular
hardware driver or browser picker UI works on every machine. A live Linux
check opened the PRISM System Audio input successfully without screen sharing;
no nonzero desktop signal was observed during that check. Synthetic browser
feeds verify analysis and rendering independently.

PowerShell installation and removal were exercised on Linux in payload-only
mode. Windows shortcut creation and browser tests are included in Windows CI.
A manual Windows desktop-audio sharing session remains a separate hardware/UI
acceptance check. Browser-owned capture indicators cannot be hidden by Prism.

Known limit: the helper follows the default output, not all independent sound
cards simultaneously. Applications explicitly routed to another output are
outside that mix. Device-label recovery may be ambiguous when two devices
have identical names; choose the desired input explicitly in that case.
