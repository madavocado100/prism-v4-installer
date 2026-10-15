# Linux audio capture model

The installed Linux edition runs a local Python host and sends mono 48 kHz PCM
from `parec` to the browser's AudioWorklet/analyser. It never falls back to the
default microphone. Standalone HTML and Windows retain browser capture.

## Outputs and virtual devices

A default recording source can be a processed microphone while the default
playback sink is a USB headset. They are independent. Capturing the former as
"desktop audio" can give microphone activity or silence instead of app playback.

**All outputs** records each physical sink monitor once. This includes USB,
HDMI, Bluetooth, and other hardware sinks exposed by PulseAudio/PipeWire.
**Default output** follows the default playback sink as it changes. An explicitly
chosen output that disappears reports an error; it never substitutes a mic.
If no physical sinks exist, All outputs uses the default sink's monitor.

A virtual echo-cancellation sink may forward into a physical output. Recording
both monitors would count that playback twice. All outputs records the final
physical monitors, including playback forwarded into them. Private microphone
processing buses are not included unless their audio actually reaches an output.

## Excluding apps

With exclusions enabled, capture switches to included playback streams using
`parec --monitor-stream=INDEX` on each stream's sink monitor. It does not mute,
move, or suspend any application's playback. All matching streams of an excluded
app are omitted. An app's stable application ID, or its binary and application
name, identifies it; process IDs are unsuitable because Flatpak uses PID
namespaces and browsers create multiple streams.

The host polls for new streams, device changes, and output changes once per
second. Virtual forwarding relationships are traced through PipeWire node groups
so apps playing into a forwarded bus remain eligible without capturing the
forwarding stream a second time. Unlabelled/infrastructure streams are omitted
when exclusions are active. Servers without per-stream monitor support may fail
this mode; a capture error is exposed in the native controls.

## Validation

The routing tests cover multiple physical outputs, echo-cancel forwarding,
multiple streams for one app, independent/private microphone buses, and missing
outputs. A real PipeWire signal test creates a temporary null sink and two test
players. It verifies that the included 440 Hz signal survives while the excluded
880 Hz signal is suppressed, and that default source/sink values are unchanged.
The null sink and test players are removed after the test. Browser tests verify
that native PCM reaches the analyser without calling microphone or screen capture.

X11 wallpaper behavior was also checked on a GNOME desktop: desktop-layer window,
2560×1440 bounds, below the desktop icon window, no startup file during a temporary
preview, and clean window/process shutdown. Automatic startup requires approval
inside the app. Wayland wallpaper integration is not implemented.
