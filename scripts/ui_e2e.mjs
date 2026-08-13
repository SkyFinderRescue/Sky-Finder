import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const BASE='https://skyfinderrescue.github.io/Sky-Finder/';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({
  viewport:{width:390,height:844},
  deviceScaleFactor:2,
  geolocation:{latitude:34.433026,longitude:-119.680869,accuracy:12},
  permissions:['geolocation','clipboard-read','clipboard-write'],
  userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1'
});
const page=await context.newPage();
const pageErrors=[];
page.on('pageerror',e=>pageErrors.push(String(e)));

async function clickPopup(locator, hostFragment){
  const popupPromise=page.waitForEvent('popup',{timeout:8000});
  await locator.click({noWaitAfter:true});
  const popup=await popupPromise;
  await popup.waitForLoadState('domcontentloaded',{timeout:8000}).catch(()=>{});
  assert.ok(popup.url().includes(hostFragment),`Expected popup ${hostFragment}, got ${popup.url()}`);
  await popup.close().catch(()=>{});
}

async function waitSnapshot(p=page){
  await p.waitForFunction(()=>{
    const t=document.getElementById('snapshotText')?.textContent||'';
    return /pilots/.test(t)&&!/Refreshing/.test(t)&&!/unavailable/i.test(t);
  },{timeout:30000});
}

try{
  await page.goto(BASE+'?e2e='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForSelector('#pilotMap',{state:'visible',timeout:15000});
  await waitSnapshot();
  await page.waitForFunction(()=>document.querySelectorAll('.pilotParaglider').length>0,{timeout:20000});
  // Ensure the final polished production revision, not the immediately prior UI build, is being served.
  await page.waitForFunction(()=>!document.body.innerText.includes('Verify pilot + timestamp in XCFind.'),{timeout:60000});
  await page.waitForFunction(()=>getComputedStyle(document.getElementById('mapSelectionText')).left==='60px',{timeout:60000});

  // Visual/layout acceptance guards.
  assert.ok(await page.locator('#brandLogo').isVisible(),'Approved brand logo is not visible');
  assert.equal(await page.locator('text=Pilot Area Map').count(),0,'Old Pilot Area Map label is visible');
  assert.equal(await page.locator('text=Verify timestamp in XCFind.').count(),0,'Old timestamp instruction is visible');
  assert.equal(await page.locator('text=Verify pilot + timestamp in XCFind.').count(),0,'Old footer verification line is visible');
  const mapBox=await page.locator('#pilotMap').boundingBox();
  assert.ok(mapBox&&mapBox.height>=390,`Mobile map too small: ${mapBox?.height}`);
  const mapCardY=(await page.locator('.mapCard').boundingBox()).y;
  const navY=(await page.locator('.navigationCard').boundingBox()).y;
  const toolsY=(await page.locator('.toolsCard').boundingBox()).y;
  assert.ok(mapCardY<navY&&navY<toolsY,'Required map -> navigation -> tools order is wrong');
  assert.ok(await page.locator('.pilotParaglider').count()>0,'Paraglider markers are missing');
  const selectionBox=await page.locator('#mapSelectionText').boundingBox();
  const zoomBox=await page.locator('.leaflet-control-zoom').boundingBox();
  assert.ok(selectionBox&&zoomBox&&selectionBox.x>=zoomBox.x+zoomBox.width+4,'Selected-pilot label overlaps map zoom controls');

  // Leaflet zoom buttons.
  assert.ok(await page.locator('.leaflet-control-zoom-in').isVisible(),'Leaflet zoom control missing');
  await page.locator('.leaflet-control-zoom-in').click();
  await sleep(250);
  await page.locator('.leaflet-control-zoom-out').click();

  // Map toolbar buttons.
  await page.locator('#fitCaliforniaBtn').click();
  await page.locator('#refreshMapBtn').click();
  await waitSnapshot();

  // GPS + current-location buttons.
  await page.locator('#gpsBtn').click();
  await page.waitForFunction(()=>document.getElementById('gpsStatus')?.classList.contains('ok'),{timeout:12000});
  assert.match(await page.locator('#gpsStatus').textContent(),/34\./);
  await page.locator('#myAreaBtn').click();
  await page.locator('#copyMyBtn').click();
  await page.waitForFunction(()=>document.getElementById('copyMyBtn')?.textContent==='Copied',{timeout:3000});
  await page.locator('#shareMyBtn').click();
  await page.waitForFunction(()=>document.getElementById('shareMyBtn')?.textContent==='Copied',{timeout:3000});

  // Select first visible pilot from the map roster.
  const firstName=(await page.locator('.mapPilotName').first().textContent()).trim();
  assert.ok(firstName,'No map pilot name available');
  await page.locator('.mapPilotCheck').first().check();
  await page.waitForFunction(()=>document.getElementById('targetCoords')?.value.trim().length>5);
  const target=await page.locator('#targetCoords').inputValue();
  assert.match(target,/-?\d+\.\d+,\s*-?\d+\.\d+/);
  assert.ok(await page.locator('#clearSelectionBtn').isVisible(),'Clear button did not appear after selection');

  // Selected-pilot XCFind verification.
  const verify=page.locator('.verifyPilotBtn').first();
  assert.ok((await verify.getAttribute('href')).includes('xcfind.paraglide.us'),'Verify XCFind target is wrong');
  await clickPopup(verify,'xcfind.paraglide.us');

  // Navigation links and target copy.
  const apple=page.locator('#appleTarget'),google=page.locator('#googleTarget');
  assert.ok((await apple.getAttribute('href')).includes('maps.apple.com'),'Apple Maps destination missing');
  assert.ok((await google.getAttribute('href')).includes('google.com/maps'),'Google Maps destination missing');
  await clickPopup(apple,'maps.apple.com');
  await clickPopup(google,'google.com');
  await page.locator('#copyTargetBtn').click();
  await page.waitForFunction(()=>document.getElementById('copyTargetBtn')?.textContent==='Copied',{timeout:3000});

  // W3W exact working implementation: embedded target + close.
  await page.locator('#w3wTarget').click();
  assert.ok(await page.locator('#w3wModal').isVisible(),'W3W modal did not open');
  const w3wSrc=await page.locator('#w3wFrame').getAttribute('src');
  assert.ok(w3wSrc?.startsWith('https://what3words.com/'),'W3W iframe target is wrong');
  assert.ok((await page.locator('#w3wFrame').getAttribute('allow'))?.includes("geolocation 'none'"),'W3W iframe geolocation is not disabled');
  await page.locator('#w3wCloseBtn').click();
  assert.ok(await page.locator('#w3wModal').isHidden(),'W3W modal did not close');

  // Remove button on selected pilot.
  await page.locator('.deselectPilotBtn').first().click();
  await page.waitForFunction(()=>document.querySelectorAll('.mapPilotCheck:checked').length===0);

  // Search + Select button.
  await page.locator('#pilotSearch').fill(firstName);
  await page.waitForFunction(()=>document.querySelectorAll('.focusPilotBtn').length>0,{timeout:5000});
  await page.locator('.focusPilotBtn').first().click();
  await page.waitForFunction(()=>document.querySelectorAll('.mapPilotCheck:checked').length===1,{timeout:5000});

  // Clear selection button.
  await page.locator('#clearSelectionBtn').click();
  await page.waitForFunction(()=>document.querySelectorAll('.mapPilotCheck:checked').length===0);

  // Pilot-list refresh button.
  await page.locator('#refreshPilotsBtn').click();
  await waitSnapshot();

  // XCFind Tracks map link.
  const tracks=page.locator('.mapOverlay a').filter({hasText:'XCFind Tracks'});
  assert.ok((await tracks.getAttribute('href')).includes('map.html?id=16'),'XCFind Tracks target is wrong');
  await clickPopup(tracks,'xcfind.paraglide.us');

  await page.screenshot({path:'skyfinder-mobile-e2e.png',fullPage:true});
  assert.deepEqual(pageErrors,[],`Page errors: ${pageErrors.join(' | ')}`);

  // Desktop/laptop responsive smoke check on the same production build.
  const desktopContext=await browser.newContext({viewport:{width:1280,height:900},geolocation:{latitude:34.433026,longitude:-119.680869,accuracy:12},permissions:['geolocation']});
  const desktop=await desktopContext.newPage();
  await desktop.goto(BASE+'?desktop-e2e='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});
  await desktop.waitForSelector('#pilotMap',{state:'visible',timeout:15000});
  await waitSnapshot(desktop);
  await desktop.waitForFunction(()=>document.querySelectorAll('.pilotParaglider').length>0,{timeout:20000});
  const desktopMap=await desktop.locator('#pilotMap').boundingBox();
  assert.ok(desktopMap&&desktopMap.height>=410,`Desktop map too small: ${desktopMap?.height}`);
  assert.ok(await desktop.locator('#brandLogo').isVisible(),'Desktop logo missing');
  assert.ok(await desktop.locator('#fitCaliforniaBtn').isVisible()&&await desktop.locator('#myAreaBtn').isVisible()&&await desktop.locator('#refreshMapBtn').isVisible(),'Desktop map toolbar controls missing');
  const dMapY=(await desktop.locator('.mapCard').boundingBox()).y,dNavY=(await desktop.locator('.navigationCard').boundingBox()).y,dToolsY=(await desktop.locator('.toolsCard').boundingBox()).y;
  assert.ok(dMapY<dNavY&&dNavY<dToolsY,'Desktop layout order is wrong');
  await desktopContext.close();

  console.log('Sky Finder production mobile button/UI E2E: PASS');
  console.log('Sky Finder desktop responsive layout smoke: PASS');
  console.log('Tested: map zoom +/-, California, My Area, map Refresh, GPS, GPS Copy, GPS Share, map pilot select, Verify XCFind, Apple Maps, Google Maps, target Copy, W3W open/close, Remove, Search+Select, Clear, pilot Refresh, XCFind Tracks.');
} finally {
  await browser.close();
}
