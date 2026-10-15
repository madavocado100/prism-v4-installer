// Run with Playwright installed: node tests/capture.cjs
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {start}=require('./server.cjs');
setTimeout(()=>{console.error('Browser check exceeded 90 seconds');process.exit(1);},90000).unref();
(async()=>{
 const server=await start();
 const browser=await chromium.launch({headless:true,channel:process.env.PRISM_TEST_CHANNEL || 'chromium',chromiumSandbox:true,...(process.env.PRISM_TEST_BROWSER ? {executablePath:process.env.PRISM_TEST_BROWSER}:{})});
 try{
  for(const hasAudio of [true,false]){
   const page=await browser.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(({hasAudio})=>{
    Object.defineProperty(navigator,'platform',{value:'Linux x86_64'});
    localStorage.setItem('prism.v4.desktop.cfg',JSON.stringify({nebula:false,clouds:false,stars:false,grid:false,aurora:false,horizon:false,bars:false,radial:false,orbits:false,strings:false,particles:false,bloom:0,grain:0}));
    window.captureCalls=[];window.focusBehavior=null;
    window.CaptureController=class{setFocusBehavior(value){window.focusBehavior=value;}};
    let ctx;
    function audio(){ctx ||= new AudioContext();const dest=ctx.createMediaStreamDestination();const osc=ctx.createOscillator();osc.connect(dest);osc.start();return dest.stream;}
    Object.defineProperty(navigator,'mediaDevices',{value:{
     enumerateDevices:async()=>[{deviceId:'desktop-loopback',groupId:'desktop',kind:'audioinput',label:'PRISM System Audio'}],
     getUserMedia:async(options)=>{window.inputOptions=options;return audio();},
     getDisplayMedia:async(options)=>{
      window.captureCalls.push(options);
      const canvas=document.createElement('canvas');
      const stream=canvas.captureStream();window.videoTrack=stream.getVideoTracks()[0];
      if(hasAudio)stream.addTrack(audio().getAudioTracks()[0]);
      return stream;
     },addEventListener(){}
    }});
   },{hasAudio});
   await page.goto(server.url);
   await page.waitForLoadState('networkidle');
 if(!await page.locator('#btn-tab').count())throw new Error('App controls missing at '+page.url()+'; title='+await page.title()+'; document='+(await page.content()).slice(0,1000));
   await page.locator('#btn-tab').click();
   await page.waitForFunction(()=>window.__prism4.source!==null,{},{timeout:4000});
   const actual=await page.evaluate(()=>({source:__prism4.source,focus:focusBehavior,options:captureCalls[0],video:videoTrack.readyState,input:window.inputOptions}));
   assert.equal(actual.focus,'no-focus-change','Tab capture must retain Prism focus');
   assert.equal(actual.options.surfaceSwitching,'exclude','Do not offer Share this tab instead');
   assert.equal(actual.options.selfBrowserSurface,'exclude');
   assert.equal(actual.options.preferCurrentTab,false);
   assert.equal(actual.video,'ended','Prism must immediately stop video capture');
   assert.equal(actual.source,hasAudio?'tab':'sys','Screen capture without audio must fall back to desktop input');
   if(!hasAudio)assert.equal(actual.input.audio.deviceId.exact,'desktop-loopback');
   assert.deepEqual(errors,[]);
   await page.close();
  }
  console.log('PASS: tab focus controls, video cleanup, silent screen capture uses whole-desktop input');
 }catch(error){console.error(error);throw error;}finally{await browser.close();await server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
