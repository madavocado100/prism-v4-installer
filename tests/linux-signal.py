"""Opt-in real Pulse/PipeWire test. Uses only an inaudible temporary sink."""
import array
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
import audio

@unittest.skipUnless(os.environ.get('PRISM_LIVE_AUDIO_TEST')=='1','Set PRISM_LIVE_AUDIO_TEST=1 on a Pulse/PipeWire desktop')
class LiveSignal(unittest.TestCase):
    def test_included_app_reaches_pcm_and_excluded_app_does_not(self):
        run=audio.command
        before=(run('pactl','get-default-sink'),run('pactl','get-default-source'))
        name='prism_validation_'+str(os.getpid())
        module=run('pactl','load-module','module-null-sink','sink_name='+name,'rate=48000','channels=2')
        players=[];mixer=None
        try:
            with tempfile.TemporaryDirectory() as folder:
                for frequency in [440,880]:
                    path=Path(folder)/f'{frequency}.wav'
                    with wave.open(str(path),'wb') as out:
                        out.setnchannels(2);out.setsampwidth(2);out.setframerate(48000)
                        out.writeframes(b''.join(struct.pack('<hh',*[int(math.sin(i*2*math.pi*frequency/48000)*8000)]*2) for i in range(48000*4)))
                    players.append(subprocess.Popen(['paplay','--client-name=PrismTest'+str(frequency),'--device='+name,str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
                time.sleep(.15)
                mixer=audio.Mixer({'output':name,'excluded':['pacat|PrismTest880']})
                samples=array.array('f')
                start=time.monotonic()
                for block in mixer.blocks():
                    if time.monotonic()-start>.4:samples.frombytes(block)
                    if time.monotonic()-start>1.3:break
                def magnitude(f):
                    return 2*abs(sum(v*complex(math.cos(i*2*math.pi*f/48000),-math.sin(i*2*math.pi*f/48000)) for i,v in enumerate(samples)))/max(1,len(samples))
                included,excluded=magnitude(440),magnitude(880)
                self.assertGreater(included,.04,'Included application audio did not reach the PCM stream')
                self.assertLess(excluded,included*.02,'Excluded application leaked into capture')
                print(f'Live PCM: included amplitude={included:.4f}; excluded amplitude={excluded:.6f}')
        finally:
            if mixer:mixer.close()
            for player in players:
                if player.poll() is None:player.terminate()
                player.wait()
            run('pactl','unload-module',module)
        self.assertEqual(before,(run('pactl','get-default-sink'),run('pactl','get-default-source')),'Capture must preserve default input/output')

if __name__=='__main__':unittest.main()
