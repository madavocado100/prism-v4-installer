const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chromium',chromiumSandbox:true,...(process.env.PRISM_TEST_BROWSER?{executablePath:process.env.PRISM_TEST_BROWSER}:{})});
 let failures=0;
 for(const scenario of ['missing microphone','stop pending permission','newest device scan','Windows desktop capture','Windows rejects tab','loopback selection']){
 const page=await browser.newPage({viewport:{width:400,height:300}});
 try{
 await page.addInitScript(({scenario})=>{
  window.inputCalls=[];window.displayCalls=[];window.pending=[];
  if(scenario.startsWith('Windows'))Object.defineProperty(navigator,'platform',{value:'Win32'});
  if(scenario==='missing microphone')localStorage.setItem('prism.v4.desktop.source',JSON.stringify({kind:'mic',id:'old-id',label:'Disconnected mic'}));
  window.testStream=()=>{const ctx=new AudioContext();const dest=ctx.createMediaStreamDestination();const osc=ctx.createOscillator();osc.connect(dest);osc.start();return dest.stream;};
  Object.defineProperty(navigator,'mediaDevices',{value:{
   enumerateDevices:async()=>scenario==='loopback selection' ? [{deviceId:'loop-one',groupId:'one',kind:'audioinput',label:'Loopback one'},{deviceId:'loop-two',groupId:'two',kind:'audioinput',label:'Loopback two'}] : [{deviceId:'camera',groupId:'camera',kind:'audioinput',label:'Camera mic'}],
   getUserMedia:options=>{window.inputCalls.push(options);if(scenario==='stop pending permission')return new Promise(resolve=>window.releaseInput=()=>{window.inputStream=testStream();resolve(inputStream);});return Promise.resolve(testStream());},
   getDisplayMedia:async options=>{window.displayCalls.push(options);const s=testStream();const v=document.createElement('canvas').captureStream().getVideoTracks()[0];v.getSettings=()=>({displaySurface:scenario==='Windows rejects tab'?'browser':'monitor'});s.addTrack(v);window.displayStream=s;return s;},
   addEventListener(){}
  }});
 },{scenario});
 await page.goto(pathToFileURL(path.resolve(__dirname,'../rgb-audio-visualizer-v4.html')).href);
 await page.waitForLoadState('networkidle');
 if(!await page.locator('#btn-tab').count())throw new Error('App controls missing at '+page.url()+'; title='+await page.title()+'; document='+(await page.content()).slice(0,1000));
 if(scenario==='missing microphone'){
  await page.evaluate(()=>__prism4.startMic());
  assert.equal(await page.evaluate(()=>inputCalls.length),0,'Missing remembered mic must not capture default input');
  assert.equal(await page.evaluate(()=>__prism4.source),null);
 }else if(scenario==='stop pending permission'){
  await page.evaluate(()=>{__prism4.startMic('default');});
  await page.waitForFunction(()=>typeof releaseInput==='function');
  await page.evaluate(()=>{__prism4.stopSource();releaseInput();});
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>__prism4.source),null,'Stop must cancel pending capture');
  assert.equal(await page.evaluate(()=>inputStream.getAudioTracks()[0].readyState),'ended');
 }else if(scenario==='newest device scan'){
  await page.evaluate(()=>{navigator.mediaDevices.enumerateDevices=()=>new Promise(resolve=>pending.push(resolve));__prism4.refreshDevices();__prism4.refreshDevices();});
  await page.evaluate(()=>pending[1]([{deviceId:'new',groupId:'new',kind:'audioinput',label:'Newest mic'}]));
  await page.evaluate(()=>pending[0]([{deviceId:'old',groupId:'old',kind:'audioinput',label:'Old scan mic'}]));
  assert.equal(await page.evaluate(()=>__prism4.inputs[0].id),'new','Old scan must not replace latest devices');
 }else if(scenario==='loopback selection'){
  await page.keyboard.press('c');
  assert.ok(await page.locator('#srcSel option[value="sys:loop-two"]').count(),'Loopback devices must be individually selectable');
  await page.locator('#srcSel').selectOption('sys:loop-two');
  await page.waitForFunction(()=>__prism4.source==='sys');
  assert.equal(await page.evaluate(()=>inputCalls.at(-1).audio.deviceId.exact),'loop-two');
  await page.reload();await page.waitForLoadState('networkidle');
 if(!await page.locator('#btn-tab').count())throw new Error('App controls missing at '+page.url()+'; title='+await page.title()+'; document='+(await page.content()).slice(0,1000));
  await page.locator('#btn-sys').click();await page.waitForFunction(()=>__prism4.source==='sys');
  assert.equal(await page.evaluate(()=>inputCalls.at(-1).audio.deviceId.exact),'loop-two','Remember selected desktop input');
 }else if(scenario==='Windows rejects tab'){
  await page.locator('#btn-sys').click();await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>__prism4.source),null,'Desktop mode must reject a shared tab');
  assert.ok(await page.evaluate(()=>displayStream.getTracks().every(t=>t.readyState==='ended')),'Rejected share tracks must close');
 }else{
  await page.locator('#btn-sys').click();
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>displayCalls.length),1,'Windows desktop audio must open native screen-audio capture');
  assert.equal(await page.evaluate(()=>displayCalls[0].video.displaySurface),'monitor');
  assert.equal(await page.evaluate(()=>__prism4.source),'sys');
 }
 console.log('PASS: '+scenario);
 }catch(e){failures++;console.error('FAIL: '+scenario+' — '+e.message);}finally{await page.close();}
 }
 await browser.close();if(failures)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
