"""Exercise per-user install, desktop launch, update and safe uninstall."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='prism installer ') as tmp:
    base = Path(tmp)
    data = base / 'data with spaces'
    subprocess.run(['bash', str(root / 'install-linux.sh'), '--data-home', str(data)], check=True)
    app = data / 'prism-v4-desktop'
    assert (app / 'config/default.json').is_file()
    # Uninstall must preserve unrelated files in an installation directory.
    sentinel = app / 'my-notes.txt'
    sentinel.write_text('keep')
    subprocess.run(['bash', str(root / 'install-linux.sh'), '--data-home', str(data)], check=True)
    assert sentinel.read_text() == 'keep'
    helper = app / 'prism-system-audio.sh'
    helper.write_text('#!/bin/sh\necho audio >> "$PRISM_TEST_LOG"\n')
    helper.chmod(0o755)
    binary = base / 'bin'
    binary.mkdir()
    brave = binary / 'brave-browser'
    brave.write_text('#!/bin/sh\nprintf "browser %s\\n" "$*" >> "$PRISM_TEST_LOG"\n')
    brave.chmod(0o755)
    log = base / 'launch.log'
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'], PRISM_TEST_LOG=str(log))
    env.pop('PRISM_BROWSER', None)
    desktop = data / 'applications/prism-v4-desktop.desktop'
    commands = [line[5:] for line in desktop.read_text().splitlines() if line.startswith('Exec=')]
    assert len(commands) == 2
    for index, command in enumerate(commands):
        subprocess.run(shlex.split(command), env=env, check=True)
        lines = log.read_text().splitlines()
        assert lines[index*2] == 'audio'
        assert lines[index*2+1].startswith('browser --app=file://')
    assert '--start-fullscreen' in log.read_text()
    subprocess.run(['bash', str(root / 'install-linux.sh'), '--data-home', str(data), '--uninstall'], check=True)
    assert sentinel.read_text() == 'keep'
    assert not desktop.exists()
    assert not (app / 'rgb-audio-visualizer-v4.html').exists()
print('PASS: Linux install/update, launcher audio initialization, fullscreen, spaces, safe uninstall')
