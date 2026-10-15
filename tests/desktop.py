"""Exercise per-user native installation, shortcuts, update and safe uninstall."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='prism installer ') as tmp:
    base=Path(tmp);data=base/'data with spaces';binary=base/'bin';binary.mkdir()
    log=base/'launch.log'
    brave=binary/'brave-browser'
    brave.write_text('#!/bin/sh\nprintf "browser %s\\n" "$*" >> "$PRISM_TEST_LOG"\n')
    brave.chmod(0o755)
    env=dict(os.environ,PATH=str(binary)+os.pathsep+os.environ['PATH'],PRISM_TEST_LOG=str(log),PRISM_BROWSER=str(brave),XDG_CONFIG_HOME=str(base/'config'),XDG_RUNTIME_DIR=str(base/'runtime'),XDG_DATA_HOME=str(data))
    install=['bash',str(root/'install-linux.sh'),'--data-home',str(data)]
    subprocess.run(install,env=env,check=True)
    app=data/'prism-v4-desktop'
    assert (app/'config/default.json').is_file()
    assert (app/'native/linux_host.py').is_file()
    sentinel=app/'my-notes.txt';sentinel.write_text('keep')
    subprocess.run(install,env=env,check=True)
    assert sentinel.read_text()=='keep'
    desktop=data/'applications/prism-v4-desktop.desktop'
    commands=[line[5:] for line in desktop.read_text().splitlines() if line.startswith('Exec=')]
    assert len(commands)==2
    try:
        for index,command in enumerate(commands):
            subprocess.run(shlex.split(command),env=env,check=True)
            deadline=time.monotonic()+4
            while (not log.exists() or len(log.read_text().splitlines())<index+1) and time.monotonic()<deadline:time.sleep(.05)
            lines=log.read_text().splitlines()
            assert lines[index].startswith('browser --user-data-dir=')
            assert '--app=file://' in lines[index]
            assert '?key=' not in lines[index], 'Secrets cannot appear in process arguments'
        assert '--start-fullscreen' in log.read_text()
        state=base/'runtime/prism-v4-desktop/host.json'
        assert state.stat().st_mode & 0o777==0o600
        assert json.loads(state.read_text())['token']
        assert not (base/'config/autostart/prism-v4-wallpaper.desktop').exists(),'Installation and normal launch cannot enable startup'
    finally:
        subprocess.run(install+['--uninstall'],env=env,check=True)
    assert sentinel.read_text()=='keep'
    assert not desktop.exists()
    assert not (app/'rgb-audio-visualizer-v4.html').exists()
print('PASS: native Linux install/update, authenticated host launch, fullscreen, spaces, no automatic startup, safe uninstall')
