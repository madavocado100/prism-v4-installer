#!/usr/bin/env python3
"""Local Linux desktop integration for PRISM. No root privileges or route edits."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audio
capture_command = audio.capture_command
APP_ID = 'prism-v4-desktop-native-v1'


def desktop_arg(value):
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value.replace('\\', '\\\\') + '"'


def ask_permission(text):
    if not shutil.which('zenity'):
        raise RuntimeError('Wallpaper setup needs zenity to display the startup permission request.')
    return subprocess.run(['zenity','--question','--title=PRISM wallpaper permission','--width=520','--ok-label=Enable wallpaper at sign-in','--cancel-label=Cancel','--text='+text]).returncode == 0


class NativeApp:
    def __init__(self, root, config_home=None, confirm=None):
        self.root = Path(root).resolve()
        home = Path(config_home or os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
        self.config = home/'prism-v4-desktop'
        self.autostart_path = home/'autostart/prism-v4-wallpaper.desktop'
        self.confirm = confirm or ask_permission
        self.token = secrets.token_urlsafe(32)
        self.url = ''
        self.wallpaper = None
        self.window = None
        self.controls = []
        self.title = 'PRISM Wallpaper ' + secrets.token_hex(6)
        self.wallpaper_key = secrets.token_urlsafe(24)
        self.control_key = secrets.token_urlsafe(24)
        self.mixers = set()
        self.lock = threading.Lock()
        self.settings = {'cfg': {}, 'audio': {'output':'all','excluded':[]}}
        try:
            saved = json.loads((self.config/'native-settings.json').read_text())
            if isinstance(saved, dict):
                self.settings.update(saved)
        except (OSError, ValueError):
            pass

    def save(self):
        self.config.mkdir(parents=True, exist_ok=True)
        self.config.chmod(0o700)
        target = self.config/'native-settings.json'
        target.write_text(json.dumps(self.settings), encoding='utf-8')
        target.chmod(0o600)

    def wallpaper_supported(self):
        return os.environ.get('XDG_SESSION_TYPE') == 'x11' and bool(os.environ.get('DISPLAY')) and all(shutil.which(x) for x in ['xdotool','xprop','zenity'])

    def browser(self):
        override = os.environ.get('PRISM_BROWSER')
        if override:
            return override
        for name in ['brave-browser','brave','google-chrome','google-chrome-stable','chromium','chromium-browser']:
            if path := shutil.which(name):
                return path
        raise RuntimeError('Install Brave, Chrome or Chromium, or set PRISM_BROWSER.')

    def open_browser(self, wallpaper=False, fullscreen=False):
        profile = self.config/('browser-wallpaper' if wallpaper else 'browser-control')
        # Keep authorization secrets out of the browser's world-readable argv.
        self.config.mkdir(parents=True, exist_ok=True)
        self.config.chmod(0o700)
        bootstrap = self.config/('open-wallpaper.html' if wallpaper else 'open-control.html')
        destination = self.url+('/wallpaper?key='+self.wallpaper_key if wallpaper else '/?key='+self.control_key)
        bootstrap.write_text('<!doctype html><meta charset="utf-8"><script>location.replace('+json.dumps(destination)+');</script>', encoding='utf-8')
        bootstrap.chmod(0o600)
        args = [self.browser(), '--user-data-dir='+str(profile), '--app='+bootstrap.as_uri(), '--class='+('PrismV4Wallpaper' if wallpaper else 'PrismV4Desktop')]
        if fullscreen:
            args.append('--start-fullscreen')
        if wallpaper:
            args += ['--autoplay-policy=no-user-gesture-required','--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding','--disable-background-timer-throttling','--no-first-run','--no-default-browser-check']
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        if not wallpaper:self.controls.append(proc)
        return proc

    def geometry(self):
        return audio.command('xdotool','getdisplaygeometry').split()

    def place_wallpaper(self, window):
        width, height = self.geometry()
        subprocess.run(['xdotool','windowunmap',window], check=True, stdout=subprocess.DEVNULL)
        for prop, kind, value in [('_NET_WM_WINDOW_TYPE','32a','_NET_WM_WINDOW_TYPE_DESKTOP'),('_NET_WM_STATE','32a','_NET_WM_STATE_BELOW, _NET_WM_STATE_STICKY, _NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER'),('_NET_WM_DESKTOP','32c','4294967295'),('_MOTIF_WM_HINTS','32c','2, 0, 0, 0, 0'),('WM_HINTS','32c','1, 0, 0, 0, 0, 0, 0, 0, 0')]:
            subprocess.run(['xprop','-id',window,'-f',prop,kind,'-set',prop,value], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['xdotool','windowsize',window,width,height,'windowmove',window,'0','0','windowmap',window], check=True, stdout=subprocess.DEVNULL)
        self.click_through(window)
        return width, height

    def click_through(self, window):
        import ctypes as c
        import ctypes.util
        x = c.CDLL(ctypes.util.find_library('X11'))
        f = c.CDLL(ctypes.util.find_library('Xfixes'))
        x.XOpenDisplay.argtypes=[c.c_char_p];x.XOpenDisplay.restype=c.c_void_p
        x.XCloseDisplay.argtypes=[c.c_void_p];x.XFlush.argtypes=[c.c_void_p]
        x.XLowerWindow.argtypes=[c.c_void_p,c.c_ulong]
        x.XQueryTree.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(c.c_ulong),c.POINTER(c.c_ulong),c.POINTER(c.POINTER(c.c_ulong)),c.POINTER(c.c_uint)]
        x.XFree.argtypes=[c.c_void_p]
        f.XFixesCreateRegion.argtypes=[c.c_void_p,c.c_void_p,c.c_int];f.XFixesCreateRegion.restype=c.c_ulong
        f.XFixesSetWindowShapeRegion.argtypes=[c.c_void_p,c.c_ulong,c.c_int,c.c_int,c.c_int,c.c_ulong]
        f.XFixesDestroyRegion.argtypes=[c.c_void_p,c.c_ulong]
        display=x.XOpenDisplay(None)
        if not display:raise RuntimeError('Cannot access the X11 desktop')
        try:
            region=f.XFixesCreateRegion(display,None,0)
            f.XFixesSetWindowShapeRegion(display,int(window),2,0,0,region)
            f.XFixesDestroyRegion(display,region)
            # GNOME reparents clients: lower the root-level frame, not just its child.
            frame=int(window)
            while True:
                root=c.c_ulong();parent=c.c_ulong();children=c.POINTER(c.c_ulong)();count=c.c_uint()
                if not x.XQueryTree(display,frame,c.byref(root),c.byref(parent),c.byref(children),c.byref(count)):break
                if children:x.XFree(children)
                if not parent.value or parent.value == root.value:break
                frame=parent.value
            x.XLowerWindow(display,frame);x.XFlush(display)
        finally:x.XCloseDisplay(display)

    def launch_wallpaper(self):
        if self.wallpaper and self.wallpaper.poll() is None and self.window:
            return
        active=subprocess.run(['xdotool','getactivewindow'],text=True,capture_output=True).stdout.strip()
        self.wallpaper = self.open_browser(True)
        deadline = time.monotonic()+20
        window = None
        while time.monotonic() < deadline:
            found = subprocess.run(['xdotool','search','--onlyvisible','--name',self.title], text=True, capture_output=True)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[-1]
                break
            if self.wallpaper.poll() is not None:
                raise RuntimeError('The wallpaper browser did not start. Check PRISM_BROWSER.')
            time.sleep(.15)
        if not window:
            self.disable_wallpaper(preserve_startup=True)
            raise RuntimeError('The wallpaper window did not appear.')
        self.window = window
        try:
            size = self.place_wallpaper(window)
        except Exception:
            self.disable_wallpaper(preserve_startup=True)
            raise
        self.window = window
        if active:subprocess.run(['xdotool','windowactivate',active],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def resize():
            nonlocal size
            while self.window == window and self.wallpaper and self.wallpaper.poll() is None:
                time.sleep(2)
                try:
                    if self.geometry() != list(size):
                        size = self.place_wallpaper(window)
                except Exception:
                    break
        threading.Thread(target=resize, daemon=True).start()

    def enable_wallpaper(self, payload):
        if not self.wallpaper_supported():
            raise RuntimeError('Live wallpaper currently requires Linux X11, xdotool, xprop and zenity. Wayland is not supported yet.')
        text = ('Allow PRISM to become your live desktop wallpaper and start at sign-in?\n\n'
                'This creates '+str(self.autostart_path)+' and starts desktop-audio capture for the visualizer. '
                'The wallpaper scales to the desktop and follows display-size changes. '
                'It does not change your microphone, output device, app routing, or the saved static wallpaper. '
                'Use Stop wallpaper in PRISM to remove the startup entry and restore the desktop.')
        if self.autostart_path.exists() and 'Name=PRISM live wallpaper' not in self.autostart_path.read_text():
            raise RuntimeError('The startup filename is already used by another launcher; it was not changed.')
        if not self.confirm(text):
            return {'cancelled': True}
        cfg = payload.get('cfg', {})
        if not isinstance(cfg, dict) or len(cfg)>200:
            raise ValueError('Invalid visualizer settings')
        self.settings['cfg'] = cfg
        self.save()
        # Validate/apply before writing persistence; failure leaves no new entry.
        self.launch_wallpaper()
        self.autostart_path.parent.mkdir(parents=True, exist_ok=True)
        self.autostart_path.write_text('[Desktop Entry]\nType=Application\nName=PRISM live wallpaper\nComment=Auto-scaled audio-reactive desktop wallpaper\nExec='+desktop_arg(self.root/'prism-v4.sh')+' --wallpaper\nTerminal=false\nX-GNOME-Autostart-enabled=true\nX-GNOME-Autostart-Delay=5\n',encoding='utf-8')
        self.autostart_path.chmod(0o644)
        return {'wallpaper':True,'autostart':True}

    @staticmethod
    def stop_browser(proc):
        if not proc:return
        # Browser launchers can be shell wrappers. Stop their dedicated session,
        # including the browser child, rather than leaving an orphaned window.
        try:
            if hasattr(proc, 'pid'):os.killpg(proc.pid, signal.SIGTERM)
            elif proc.poll() is None:proc.terminate()
        except ProcessLookupError:pass
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                if hasattr(proc, 'pid'):os.killpg(proc.pid, signal.SIGKILL)
                else:proc.kill()
            except ProcessLookupError:pass
            proc.wait(timeout=3)

    def disable_wallpaper(self, preserve_startup=False):
        window, self.window = self.window, None
        if window:
            subprocess.run(['xdotool','windowclose',window],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.stop_browser(self.wallpaper)
        self.wallpaper = None
        if not preserve_startup and self.autostart_path.exists() and 'PRISM live wallpaper' in self.autostart_path.read_text():
            self.autostart_path.unlink()
        return {'wallpaper':False,'autostart':False}

    def info(self):
        try:
            routes = audio.describe(audio.inventory())
            error = ''
        except Exception as exc:
            routes = {'outputs':[],'apps':[]}
            error = str(exc)
        return {'linux':True,'desktopAudio':all(shutil.which(x) for x in ['parec','pactl']),'wallpaperSupported':self.wallpaper_supported(),'wallpaperActive':bool(self.window and self.wallpaper and self.wallpaper.poll() is None),'autostart':self.autostart_path.exists(),'audio':self.settings['audio'],'routes':routes,'error':error,'captureError':next((m.error for m in list(self.mixers) if m.error),'')}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    @property
    def app(self):
        return self.server.app

    def trusted(self, token=True):
        origin = self.headers.get('Origin')
        host = self.headers.get('Host')
        return host == self.server.address and (not origin or origin == self.app.url) and (not token or secrets.compare_digest(self.headers.get('X-Prism-Token',''),self.app.token))

    def reply(self, data, status=200, content='application/json'):
        raw = json.dumps(data).encode() if content == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type',content)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        route = urlsplit(self.path).path
        if not self.trusted(token=False):
            self.reply({'error':'Untrusted origin'},403)
            return
        if route == '/health':
            self.reply({'app':APP_ID,'pid':os.getpid()})
        elif route in ['/', '/wallpaper']:
            from urllib.parse import parse_qs
            expected = self.app.wallpaper_key if route == '/wallpaper' else self.app.control_key
            if parse_qs(urlsplit(self.path).query).get('key') != [expected]:
                self.reply({'error':'Open PRISM using its installed launcher'},403)
                return
            native = {'token':self.app.token,'wallpaper':route == '/wallpaper','cfg':self.app.settings['cfg'],'audio':self.app.settings['audio']}
            script = '<script>window.__PRISM_NATIVE__='+json.dumps(native).replace('<','\\u003c')+';</script>'
            html = (self.app.root/'rgb-audio-visualizer-v4.html').read_text()
            html = html.replace('<head>','<head>'+script,1)
            if route == '/wallpaper':
                start = html.index('<title>');end = html.index('</title>',start)
                html = html[:start]+'<title>'+self.app.title+html[end:]
            self.reply(html.encode(),content='text/html; charset=utf-8')
        elif not self.trusted():
            self.reply({'error':'Native authorization required'},403)
        elif route == '/native/state':
            self.reply({'cfg':self.app.settings['cfg'],'captureError':next((m.error for m in list(self.app.mixers) if m.error),'')})
        elif route == '/native/info':
            self.reply(self.app.info())
        elif route == '/native/audio':
            mixer = None
            try:
                mixer = audio.Mixer(self.app.settings['audio'])
                self.app.mixers.add(mixer)
                self.send_response(200)
                self.send_header('Content-Type','application/octet-stream')
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Prism-Sample-Rate','48000')
                self.send_header('Connection','close')
                self.end_headers()
                for block in mixer.blocks():
                    self.wfile.write(block)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as error:
                if mixer is None:
                    self.reply({'error':str(error)},503)
            finally:
                if mixer:
                    mixer.close()
                    self.app.mixers.discard(mixer)
        else:
            self.reply({'error':'Not found'},404)

    def do_POST(self):
        if not self.trusted():
            self.reply({'error':'Native authorization required'},403)
            return
        try:
            size = int(self.headers.get('Content-Length','0'))
            if size < 0 or size > 65536:
                raise ValueError('Request too large')
            payload = json.loads(self.rfile.read(size) or '{}')
            if not isinstance(payload,dict):
                raise ValueError('Object required')
            route = urlsplit(self.path).path
            if route == '/native/wallpaper':
                with self.app.lock:
                    result = self.app.enable_wallpaper(payload)
            elif route == '/native/wallpaper/stop':
                result = self.app.disable_wallpaper()
            elif route == '/native/settings':
                cfg = payload.get('cfg')
                if not isinstance(cfg,dict) or len(cfg)>200:
                    raise ValueError('Invalid visualizer settings')
                self.app.settings['cfg'] = cfg
                self.app.save()
                result = {'saved':True}
            elif route == '/native/audio-selection':
                output, excluded = payload.get('output','all'), payload.get('excluded',[])
                if not isinstance(output,str) or not isinstance(excluded,list) or len(excluded)>100 or any(not isinstance(x,str) or len(x)>512 for x in excluded):
                    raise ValueError('Invalid audio selection')
                audio.plan(audio.inventory(),{'output':output,'excluded':excluded})
                self.app.settings['audio'] = {'output':output,'excluded':excluded}
                self.app.save()
                for mixer in list(self.app.mixers):
                    mixer.selection = dict(self.app.settings['audio'])
                    mixer.update()
                result = self.app.info()
            elif route == '/native/open':
                if payload.get('wallpaper'):
                    if not self.app.autostart_path.exists():
                        raise ValueError('Enable wallpaper from the app first to approve startup capture.')
                    self.app.launch_wallpaper()
                else:
                    self.app.open_browser(fullscreen=bool(payload.get('fullscreen')))
                result = {'opened':True}
            elif route == '/native/quit':
                self.app.disable_wallpaper(bool(payload.get('preserveStartup')))
                for proc in self.app.controls:
                    self.app.stop_browser(proc)
                for mixer in list(self.app.mixers):mixer.close()
                threading.Thread(target=self.server.shutdown,daemon=True).start()
                result = {'stopped':True}
            else:
                self.reply({'error':'Not found'},404)
                return
            self.reply(result)
        except Exception as error:
            self.reply({'error':str(error)},400)


def serve(root, runtime, wallpaper=False, fullscreen=False):
    import fcntl
    runtime.mkdir(parents=True,exist_ok=True)
    runtime.chmod(0o700)
    lock = (runtime/'host.lock').open('w')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        return
    app = NativeApp(root)
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.daemon_threads = True
    server.app = app
    server.address = '127.0.0.1:'+str(server.server_port)
    app.url = 'http://'+server.address
    state = runtime/'host.json'
    state.write_text(json.dumps({'url':app.url,'token':app.token,'pid':os.getpid(),'root':str(root)}))
    state.chmod(0o600)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    import signal
    def stop_signal(*unused):server.shutdown()
    signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
    try:
        if wallpaper:
            if not app.autostart_path.exists():raise RuntimeError('Wallpaper startup has not been approved in the app.')
            app.launch_wallpaper()
        else:
            app.open_browser(fullscreen=fullscreen)
            if app.autostart_path.exists() and app.wallpaper_supported():app.launch_wallpaper()
        while server._BaseServer__is_shut_down.is_set() is False:
            time.sleep(.25)
    finally:
        app.disable_wallpaper(preserve_startup=True)
        for proc in app.controls:
            app.stop_browser(proc)
        for mixer in list(app.mixers):mixer.close()
        server.shutdown()
        server.server_close()
        state.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wallpaper',action='store_true')
    parser.add_argument('--stop',action='store_true')
    parser.add_argument('--shutdown-for-update',action='store_true')
    parser.add_argument('--start-fullscreen',action='store_true')
    parser.add_argument('--serve',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR') or Path.home()/'.cache')/'prism-v4-desktop'
    if args.serve:
        serve(root,runtime,args.wallpaper,args.start_fullscreen)
        return
    try:
        state = json.loads((runtime/'host.json').read_text())
        with urlopen(state['url']+'/health',timeout=2) as response:
            health = json.load(response)
        if health != {'app':APP_ID,'pid':state['pid']}:
            raise ValueError('Unrecognized local server')
        request = Request(state['url']+('/native/quit' if args.stop or args.shutdown_for_update else '/native/open'),data=json.dumps({'wallpaper':args.wallpaper,'fullscreen':args.start_fullscreen,'preserveStartup':args.shutdown_for_update}).encode(),headers={'X-Prism-Token':state['token'],'Content-Type':'application/json'})
        with urlopen(request,timeout=30) as response:
            json.load(response)
        return
    except (OSError,ValueError):
        if args.stop:
            NativeApp(root).disable_wallpaper()
            return
        if args.shutdown_for_update:return
    runtime.mkdir(parents=True,exist_ok=True)
    runtime.chmod(0o700)
    with (runtime/'host.log').open('a') as log:
        proc = subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve']+(['--wallpaper'] if args.wallpaper else [])+(['--start-fullscreen'] if args.start_fullscreen else []),stdout=log,stderr=log,start_new_session=True)
    for _ in range(50):
        if (runtime/'host.json').exists():return
        if proc.poll() is not None:raise RuntimeError('Native host failed; see '+str(runtime/'host.log'))
        time.sleep(.1)
    raise RuntimeError('Native host did not start; see '+str(runtime/'host.log'))

if __name__ == '__main__':main()
