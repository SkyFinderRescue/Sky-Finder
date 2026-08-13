import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const BASE='https://skyfinderrescue.github.io/Sky-Finder/';
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({
  viewport:{width:390,height:844},
  deviceScaleFactor:2,
  geolocation:{latitude:34.433026,longitude:-119.680869,accuracy:12},
  permissions:['geolocation'],
  userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1'
});
const page=await context.newPage();
try {
  await page.goto(BASE+'?auto-gps-e2e='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForSelector('#pilotMap',{state:'visible',timeout:15000});
  await page.waitForFunction(()=>document.querySelectorAll('.mapPilotCheck').length>0,{timeout:30000});
  assert.equal((await page.locator('#w3wTarget').textContent()).trim(),'what3words');
  assert.equal(await page.locator('.mapOverlay a').filter({hasText:'XCFind Tracks'}).count(),0);
  assert.equal(await page.locator('.verifyPilotBtn').count(),0);

  // Do not press Use GPS. Pilot selection itself must request responder GPS.
  await page.locator('.mapPilotCheck').first().check();
  await page.waitForFunction(()=>document.getElementById('gpsStatus')?.classList.contains('ok'),{timeout:15000});
  await page.waitForFunction(()=>/mi$/.test(document.getElementById('distanceValue')?.textContent||'') && /°/.test(document.getElementById('bearingValue')?.textContent||''),{timeout:15000});

  const distance=(await page.locator('#distanceValue').textContent()).trim();
  const bearing=(await page.locator('#bearingValue').textContent()).trim();
  assert.match(distance,/^\d+(?:\.\d+)? mi$/);
  assert.match(bearing,/^\d+° (?:N|NE|E|SE|S|SW|W|NW)$/);
  assert.ok(await page.locator('#metrics').isVisible(),'Metrics must be visible after pilot selection');

  const linksBox=await page.locator('.targetLinks').boundingBox();
  const metricsBox=await page.locator('#metrics').boundingBox();
  assert.ok(linksBox&&metricsBox&&metricsBox.y>=linksBox.y+linksBox.height,'Distance/bearing must be below what3words and Copy buttons');

  console.log(`Sky Finder pilot-selection auto GPS metrics: PASS (${distance}, ${bearing})`);
} finally {
  await browser.close();
}
