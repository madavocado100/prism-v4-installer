const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
setTimeout(()=>{console.error('Native browser test timed out');process.exit(1);},60000).unref();
(async()=>{
 const server=spawn('python3',['-u',path.join(__dirname,'native-server.py')]);
 let browser;
 try{
  const info=await new Promise((resolve,reject)=>{let data='';server.stdout.on('data',c=>{data+=c;if(data.includes('\n'))resolve(JSON.parse(data.split('\n')[0]));});server.on('exit',code=>reject(new Error('Fixture server exited '+code)));server.stderr.on('data',c=>process.stderr.write(c));});
  const forbidden=await fetch(info.url+'/native/info');assert.equal(forbidden.status,403);
  const badOrigin=await fetch(info.url+'/native/info',{headers:{'X-Prism-Token':info.token,Origin:'https://untrusted.example'}});assert.equal(badOrigin.status,403);
  const root=await fetch(info.url+'/');assert.equal(root.status,403);
  const view=await fetch(info.url+'/wallpaper');assert.equal(view.status,403);
  browser=await chromium.launch({headless:true,channel:process.env.PRISM_TEST_CHANNEL||'chromium',chromiumSandbox:true,...(process.env.PRISM_TEST_BROWSER?{executablePath:process.env.PRISM_TEST_BROWSER}:{})});
  const page=await browser.newPage({viewport:{width:850,height:700}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=()=>{throw new Error('Desktop mode must not capture the microphone');};navigator.mediaDevices.getDisplayMedia=()=>{throw new Error('Desktop mode must not share a screen/tab');};});
  await page.goto(info.page);await page.locator('#btn-sys').click();
  await page.waitForFunction(()=>__prism4.source==='sys'&&__prism4.metrics.rms>.05,{},{timeout:10000});
  assert.ok(await page.evaluate(()=>__prism4.metrics.rms)>.05,'Native PCM must reach the analyser');
  await page.keyboard.press('c');
  await page.locator('#nativeOutput').selectOption('default');
  await page.waitForFunction(()=>document.getElementById('nativeOutput').value==='default');
  await page.getByLabel('Exclude Test player').check();
  await page.waitForFunction(()=>document.querySelector('#nativeApps input').checked);
  await page.locator('#btnWallpaper').click();
  await page.waitForTimeout(300);
  assert.equal(fs.existsSync(info.startup),false,'Cancelled native approval must not create startup');
  await page.evaluate(()=>__prism4.stopSource());
  assert.equal(await page.evaluate(()=>__prism4.source),null);
  assert.deepEqual(errors,[]);
  console.log('PASS: protected native API, actual PCM analyser signal, output/exclusion controls, cancelled wallpaper permission, capture stop');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
