"""Per-user Linux installation; leaves the original Prism v4 untouched."""
import argparse
import os
from pathlib import Path
import shutil
import sys
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-home', type=Path, default=Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share'))
parser.add_argument('--uninstall', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
base = args.data_home.expanduser().resolve()
dest = base / 'prism-v4-desktop'
shortcut = base / 'applications/prism-v4-desktop.desktop'
files = ['rgb-audio-visualizer-v4.html', 'prism-v4.sh', 'prism-system-audio.sh', 'README.md', 'LINUX-AUDIO.md', 'config/default.json', 'native/audio.py', 'native/linux_host.py']

def exec_arg(value):
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value.replace('\\', '\\\\') + '"'

env = dict(os.environ)
if args.uninstall:
    host = dest / 'native/linux_host.py'
    if host.exists():subprocess.run([sys.executable,str(host),'--stop'],env=env,check=False)
    for name in files:
        (dest / name).unlink(missing_ok=True)
    shortcut.unlink(missing_ok=True)
    for cache in (dest/'native').glob('__pycache__/*.pyc'):
        if cache.name.startswith(('audio.', 'linux_host.')):cache.unlink()
    for folder in [dest/'native/__pycache__',dest/'native',dest / 'config', dest]:
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    print('Uninstalled Prism v4 Desktop Audio; browser settings and other files preserved.')
    sys.exit(0)

if root == dest:
    parser.error('Run the installer from the extracted distribution, not the installed application directory.')
existing = dest/'native/linux_host.py'
if existing.exists():subprocess.run([sys.executable,str(existing),'--shutdown-for-update'],env=env,check=False)
for name in files:
    target = dest / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / name, target)
for name in ['prism-v4.sh', 'prism-system-audio.sh']:
    (dest / name).chmod(0o755)
shortcut.parent.mkdir(parents=True, exist_ok=True)
command = exec_arg(dest / 'prism-v4.sh')
shortcut.write_text(f'''[Desktop Entry]
Type=Application
Name=PRISM v4 Desktop Audio
Comment=Audio visualizer with whole-desktop capture
Exec={command}
Icon=multimedia-volume-control
Terminal=false
Categories=AudioVideo;Player;
StartupWMClass=PrismV4Desktop
Actions=fullscreen;

[Desktop Action fullscreen]
Name=PRISM Desktop Audio (fullscreen)
Exec={command} --start-fullscreen
''', encoding='utf-8')
shortcut.chmod(0o755)
print(f'Installed {dest}\nShortcut: {shortcut}')
missing = [name for name in ['parec', 'pactl', 'xdotool', 'xprop', 'zenity'] if not shutil.which(name)]
if missing:
    print('For native desktop audio/wallpaper, install the packages providing: ' + ', '.join(missing))
