"""Read-only PulseAudio/PipeWire capture. Never changes defaults or routes apps."""
import array
from collections import deque
import json
import os
import subprocess
import sys
import threading
import time

RATE = 48000
FRAMES = 1024


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE, timeout=4).strip()


def app_key(stream):
    p = stream.get('properties', {})
    if not p.get('application.name') or str(p.get('node.virtual', '')).lower() == 'true':
        return None
    # Flatpak PIDs are namespace-local. Identity must not depend on a PID.
    return p.get('application.id') or p.get('application.process.binary', '') + '|' + p['application.name']


def capture_command(source, stream=None):
    result = ['parec', '--device=' + source, '--format=float32le', '--rate=48000', '--channels=1', '--latency-msec=60']
    if stream is not None:
        result.append('--monitor-stream=' + str(stream))
    return result


def inventory():
    data = {name: json.loads(command('pactl', '-f', 'json', 'list', name)) for name in ['sinks', 'sink-inputs', 'sources', 'source-outputs']}
    data['default'] = command('pactl', 'get-default-sink')
    return data


def physical(sink):
    p = sink.get('properties', {})
    return str(p.get('node.virtual', '')).lower() != 'true' and ('HARDWARE' in sink.get('flags', []) or p.get('device.api') in ['alsa', 'bluez5', 'jack'])


def reachable_sinks(data, targets):
    """Trace virtual forwarding towards selected outputs without capturing both."""
    reachable = set(targets)
    sinks = {s['index']: s for s in data['sinks']}
    monitors = {s['monitor_source']: s['index'] for s in data['sinks']}
    source_sink = {s['index']: monitors[s['name']] for s in data['sources'] if s['name'] in monitors}
    edges = []
    for output in data['sink-inputs']:
        group = output.get('properties', {}).get('node.link-group') or output.get('properties', {}).get('node.group')
        if not group:
            continue
        for source in data['source-outputs']:
            props = source.get('properties', {})
            if (props.get('node.link-group') or props.get('node.group')) == group and source['source'] in source_sink:
                edges.append((source_sink[source['source']], output['sink']))
        # Native echo-cancel adapters forward their virtual playback sink in
        # the same node group, without a separate monitor source-output.
        for sink in sinks.values():
            if sink.get('properties', {}).get('node.group') == group and sink['index'] != output['sink']:
                edges.append((sink['index'], output['sink']))
    changed = True
    while changed:
        changed = False
        for source, dest in edges:
            if dest in reachable and source not in reachable:
                reachable.add(source)
                changed = True
    return reachable


def plan(data, selection):
    sinks = data['sinks']
    chosen = selection.get('output', 'all')
    if chosen == 'all':
        targets = [s for s in sinks if physical(s)]
        if not targets:
            targets = [s for s in sinks if s['name'] == data['default']]
    else:
        name = data['default'] if chosen == 'default' else chosen
        targets = [s for s in sinks if s['name'] == name]
    if not targets:
        raise RuntimeError('The selected audio output is unavailable; choose another output.')
    excluded = set(selection.get('excluded', []))
    if not excluded:
        return [(s['monitor_source'], None) for s in targets]
    audible = reachable_sinks(data, {s['index'] for s in targets})
    by_index = {s['index']: s for s in sinks}
    result = []
    for stream in data['sink-inputs']:
        key = app_key(stream)
        if key and key not in excluded and stream['sink'] in audible and not stream.get('corked') and not stream.get('mute'):
            result.append((by_index[stream['sink']]['monitor_source'], stream['index']))
    return result


def describe(data):
    apps = {}
    for stream in data['sink-inputs']:
        key = app_key(stream)
        if key:
            apps[key] = {'key': key, 'name': stream['properties']['application.name']}
    return {'default': data['default'], 'outputs': [{'name': s['name'], 'label': s.get('description', s['name']), 'physical': physical(s)} for s in data['sinks']], 'apps': sorted(apps.values(), key=lambda a: a['name'].lower())}


class Recorder:
    def __init__(self, source, stream):
        self.queue = deque(maxlen=8)
        self.error = ''
        self.proc = subprocess.Popen(capture_command(source, stream), stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self):
        data = bytearray()
        while chunk := self.proc.stdout.read(FRAMES * 4):
            data.extend(chunk)
            while len(data) >= FRAMES * 4:
                block = array.array('f')
                block.frombytes(data[:FRAMES * 4])
                if sys.byteorder != 'little':
                    block.byteswap()
                del data[:FRAMES * 4]
                self.queue.append(block)
        self.error = self.proc.stderr.read(4096).decode(errors='replace').strip()

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.thread.join(timeout=2)
        self.proc.stdout.close()
        self.proc.stderr.close()


class Mixer:
    def __init__(self, selection, load=inventory):
        self.selection = dict(selection)
        self.load = load
        self.recorders = {}
        self.closed = False
        self.lock = threading.RLock()
        self.error = ''
        try:
            self.update()
        except Exception:
            self.close()
            raise
        threading.Thread(target=self.watch, daemon=True).start()

    def update(self):
        try:
            wanted = set(plan(self.load(), self.selection))
        except Exception:
            # An unplugged selection must not keep recording an old monitor.
            with self.lock:self._reconcile(set())
            raise
        with self.lock:
            if self.closed:
                return
            self.error = ''
            self._reconcile(wanted)

    def _reconcile(self, wanted):
        for key in list(self.recorders):
            recorder = self.recorders[key]
            if key not in wanted or recorder.proc.poll() is not None:
                recorder.close()
                self.error = recorder.error
                self.recorders.pop(key, None)
        for key in wanted:
            if key not in self.recorders:
                self.recorders[key] = Recorder(*key)

    def watch(self):
        while not self.closed:
            time.sleep(1)
            try:
                self.update()
            except Exception as error:
                self.error = str(error)

    def blocks(self):
        deadline = time.monotonic()
        while not self.closed:
            samples = [0.0] * FRAMES
            for recorder in list(self.recorders.values()):
                block = recorder.queue.popleft() if recorder.queue else None
                if block is not None:
                    samples = [a + b for a, b in zip(samples, block)]
            out = array.array('f', (max(-1.0, min(1.0, value)) for value in samples))
            if sys.byteorder != 'little':
                out.byteswap()
            yield out.tobytes()
            deadline += FRAMES / RATE
            delay = deadline - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            elif delay < -.2:
                deadline = time.monotonic()

    def close(self):
        with self.lock:
            self.closed = True
            for recorder in list(self.recorders.values()):
                recorder.close()
            self.recorders.clear()
