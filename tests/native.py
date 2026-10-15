"""Native integration contracts: no startup changes without native approval."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import os
import subprocess
import sys
import threading
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

root = Path(__file__).resolve().parents[1]

class NativeTests(unittest.TestCase):
    def module(self):
        path = root / 'native/linux_host.py'
        self.assertTrue(path.exists(), 'Linux native integration must be implemented')
        spec = importlib.util.spec_from_file_location('prism_native', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_cancel_cannot_create_startup_or_launch_wallpaper(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as folder:
            app = module.NativeApp(root, Path(folder), confirm=lambda text: False)
            app.wallpaper_supported = lambda: True
            launched = []
            app.launch_wallpaper = lambda: launched.append(True)
            self.assertEqual(app.enable_wallpaper({}), {'cancelled': True})
            self.assertFalse(app.autostart_path.exists())
            self.assertEqual(launched, [])

    def test_approval_creates_owned_scaled_wallpaper_launcher(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as folder:
            app = module.NativeApp(root, Path(folder), confirm=lambda text: True)
            app.wallpaper_supported = lambda: True
            app.launch_wallpaper = lambda: None
            app.enable_wallpaper({})
            self.assertTrue(app.autostart_path.exists())
            text = app.autostart_path.read_text()
            self.assertIn('--wallpaper', text)
            self.assertIn('X-GNOME-Autostart-enabled=true', text)
            app.disable_wallpaper()
            self.assertFalse(app.autostart_path.exists())

    def test_control_page_cannot_reveal_token_without_bootstrap_key(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as folder:
            app=module.NativeApp(root,Path(folder))
            server=ThreadingHTTPServer(('127.0.0.1',0),module.Handler)
            server.app=app;server.address='127.0.0.1:'+str(server.server_port);app.url='http://'+server.address
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with self.assertRaises(HTTPError) as failure:urlopen(app.url+'/',timeout=2)
                self.assertEqual(failure.exception.code,403)
                with urlopen(app.url+'/?key='+app.control_key,timeout=2) as response:
                    self.assertIn(app.token.encode(),response.read())
            finally:server.shutdown();server.server_close();thread.join()

    def test_offline_stop_removes_owned_startup(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);app=module.NativeApp(root,base/'config')
            app.autostart_path.parent.mkdir(parents=True)
            app.autostart_path.write_text('[Desktop Entry]\nName=PRISM live wallpaper\n')
            env=dict(os.environ,XDG_CONFIG_HOME=str(base/'config'),XDG_RUNTIME_DIR=str(base/'runtime'))
            subprocess.run([sys.executable,str(root/'native/linux_host.py'),'--stop'],env=env,check=True)
            self.assertFalse(app.autostart_path.exists(),'Offline stop must remove owned startup')

    def test_failed_window_placement_cannot_become_persistent_on_retry(self):
        module=self.module()
        class Process:
            def __init__(self):self.stopped=False
            def poll(self):return 0 if self.stopped else None
            def terminate(self):self.stopped=True
            def kill(self):self.stopped=True
            def wait(self,timeout=None):return 0
        with tempfile.TemporaryDirectory() as folder:
            app=module.NativeApp(root,Path(folder),confirm=lambda text:True)
            app.wallpaper_supported=lambda:True
            started=[]
            def open_browser(*args):
                proc=Process();started.append(proc);return proc
            app.open_browser=open_browser
            app.place_wallpaper=lambda window:(_ for _ in ()).throw(RuntimeError('placement failed'))
            with patch.object(module.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='123\n')):
                for attempt in range(2):
                    with self.assertRaises(RuntimeError):app.enable_wallpaper({})
                    self.assertIsNone(app.wallpaper)
                    self.assertFalse(app.autostart_path.exists())
            self.assertTrue(all(p.stopped for p in started))

    def test_browser_bootstrap_keeps_secrets_out_of_process_arguments(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as folder:
            app=module.NativeApp(root,Path(folder));app.url='http://127.0.0.1:12345'
            app.browser=lambda:'/fake/browser'
            with patch.object(module.subprocess,'Popen') as launch:
                app.open_browser()
                args=launch.call_args.args[0]
                self.assertFalse(any(app.control_key in arg or app.token in arg for arg in args))
                self.assertTrue(any(arg.startswith('--app=file://') for arg in args))
            bootstrap=app.config/'open-control.html'
            self.assertIn(app.control_key,bootstrap.read_text())
            self.assertEqual(bootstrap.stat().st_mode & 0o777,0o600)
            self.assertEqual(app.config.stat().st_mode & 0o777,0o700)

    def test_desktop_capture_targets_monitor_not_microphone(self):
        module = self.module()
        self.assertEqual(module.capture_command('speakers.monitor'), ['parec','--device=speakers.monitor','--format=float32le','--rate=48000','--channels=1','--latency-msec=60'])

if __name__ == '__main__':
    unittest.main()
