"""Controlled PCM server for browser integration tests; never accesses real audio."""
import array
from http.server import ThreadingHTTPServer
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import time

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('host',root/'native/linux_host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
fixture={'default':'speakers','sinks':[{'index':1,'name':'speakers','description':'Test speakers','monitor_source':'speakers.monitor','flags':['HARDWARE'],'properties':{}}],'sources':[],'source-outputs':[],'sink-inputs':[{'index':10,'sink':1,'properties':{'application.name':'Test player','application.process.binary':'player'}}]}
host.audio.inventory=lambda:fixture
class ToneMixer:
    def __init__(self,selection):self.selection=selection;self.closed=False;self.error=''
    def blocks(self):
        n=0
        while not self.closed:
            block=array.array('f',(math.sin((n+i)*2*math.pi*440/48000)*.35 for i in range(1024)))
            yield block.tobytes();n+=1024;time.sleep(1024/48000)
    def update(self):pass
    def close(self):self.closed=True
host.audio.Mixer=ToneMixer
with tempfile.TemporaryDirectory(prefix='prism-native-browser-') as folder:
    app=host.NativeApp(root,Path(folder),confirm=lambda text:False)
    app.wallpaper_supported=lambda:True
    app.settings['cfg']={'nebula':False,'clouds':False,'stars':False,'grid':False,'aurora':False,'horizon':False,'bars':False,'orbits':False,'radial':False,'particles':False,'bloom':0}
    server=ThreadingHTTPServer(('127.0.0.1',0),host.Handler);server.daemon_threads=True
    server.app=app;server.address='127.0.0.1:'+str(server.server_port);app.url='http://'+server.address
    print(json.dumps({'url':app.url,'page':app.url+'/?key='+app.control_key,'token':app.token,'startup':str(app.autostart_path)}),flush=True)
    server.serve_forever()
