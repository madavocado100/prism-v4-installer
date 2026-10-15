import sys
from pathlib import Path
import unittest
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
import audio

class Routes(unittest.TestCase):
    def data(self):
        def sink(i, name, hardware=False, group=''):
            return {'index': i, 'name': name, 'monitor_source': name+'.monitor', 'flags': ['HARDWARE'] if hardware else [], 'properties': {'node.virtual': str(not hardware).lower(), 'node.group': group}}
        def stream(i, sink, name, group='', virtual=False):
            return {'index':i,'sink':sink,'properties':{'application.name':name,'application.process.binary':name,'application.process.id':'9','node.group':group,'node.virtual':str(virtual).lower()}}
        return {'default':'headphones','sinks':[sink(1,'headphones',True),sink(2,'speakers',True),sink(3,'echo',False,'aec'),sink(4,'private-mic')], 'sources':[{'index':11,'name':'headphones.monitor'},{'index':13,'name':'echo.monitor'},{'index':14,'name':'private-mic.monitor'}], 'source-outputs':[], 'sink-inputs':[stream(20,1,'Brave'),stream(21,1,'Brave'),stream(22,3,'Vesktop'),stream(23,1,'AEC','aec',True),stream(24,4,'Private translator')]}

    def test_whole_desktop_records_final_hardware_outputs_once(self):
        self.assertEqual(audio.plan(self.data(),{'output':'all'}),[('headphones.monitor',None),('speakers.monitor',None)])

    def test_exclusion_groups_multiple_app_streams_without_pid_matching(self):
        data=self.data()
        self.assertEqual(audio.plan(data,{'excluded':['Brave|Brave']}),[('echo.monitor',22)])
        self.assertEqual(len(audio.describe(data)['apps']),3)

    def test_private_mic_bus_is_not_desktop_audio(self):
        plans=audio.plan(self.data(),{'excluded':['not-present']})
        self.assertNotIn(('private-mic.monitor',24),plans)

    def test_disappearing_output_closes_previous_monitor(self):
        class Recorder:
            error=''
            closed=False
            def close(self):self.closed=True
        recorder=Recorder()
        mixer=audio.Mixer.__new__(audio.Mixer)
        mixer.selection={'output':'unplugged'};mixer.load=self.data
        mixer.recorders={('headphones.monitor',None):recorder}
        mixer.lock=threading.RLock();mixer.closed=False
        with self.assertRaises(RuntimeError):mixer.update()
        self.assertTrue(recorder.closed)
        self.assertEqual(mixer.recorders,{})

    def test_missing_output_fails_without_microphone_fallback(self):
        with self.assertRaises(RuntimeError):audio.plan(self.data(),{'output':'unplugged'})

if __name__=='__main__':unittest.main()
