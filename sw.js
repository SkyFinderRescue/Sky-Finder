const CACHE = 'sky-finder-v1.4.2';
const SHELL = ['./','./index.html','./manifest.webmanifest','./assets/icon.svg'];

function transformIndex(html) {
  return html
    .replace(
      '<div class="pilotActions"><button class="btn primary usePilotBtn" type="button" data-pilot-id="${escapeHtml(id)}" data-lat="${Number(p.lat)}" data-lng="${Number(p.lng)}" data-name="${escapeHtml(p.name||\'Pilot\')}">Use Last Point</button><a class="btn verifyPilotBtn" href="${pilotDetailUrl(p)}" target="_blank" rel="noopener noreferrer">Verify XCFind</a></div>',
      '<div class="pilotActions"><a class="btn verifyPilotBtn" href="${pilotDetailUrl(p)}" target="_blank" rel="noopener noreferrer">Verify XCFind</a></div>'
    )
    .replace(
      '.pilotActions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}',
      '.pilotActions{display:grid;grid-template-columns:1fr;gap:7px;margin-top:9px}'
    )
    .replace(
      '@media(max-width:470px){.pilotActions{grid-template-columns:1fr 1fr}.targetLinks{grid-template-columns:1fr 1fr}}',
      '@media(max-width:470px){.pilotActions{grid-template-columns:1fr}.targetLinks{grid-template-columns:1fr 1fr}}'
    )
    .replace(
      'const validIds=new Set(allPilots().map(pilotId));[...selectedPilotIds].forEach(id=>{if(!validIds.has(id))selectedPilotIds.delete(id)});syncMapMarkers();renderSelectionState()',
      'const validIds=new Set(allPilots().map(pilotId));[...selectedPilotIds].forEach(id=>{if(!validIds.has(id))selectedPilotIds.delete(id)});const activeTargetId=[...selectedPilotIds].at(-1);if(activeTargetId)setPilotAsTarget(activeTargetId);syncMapMarkers();renderSelectionState()'
    )
    .replace(
      "els.pilotList.addEventListener('click',e=>{const use=e.target.closest?e.target.closest('.usePilotBtn'):null;if(use){const lat=Number(use.dataset.lat),lng=Number(use.dataset.lng);if(!Number.isFinite(lat)||!Number.isFinite(lng))return;els.targetCoords.value=`${fmt(lat)}, ${fmt(lng)}`;updateTarget();els.targetStatus.textContent=`${use.dataset.name||'Pilot'}: ${coordText({lat,lng})}`;return}const focus=e.target.closest?e.target.closest('.focusPilotBtn'):null;",
      "els.pilotList.addEventListener('click',e=>{const focus=e.target.closest?e.target.closest('.focusPilotBtn'):null;"
    );
}

async function transformedNavigationResponse(request) {
  const response = await fetch(request);
  if (!response.ok) return response;
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('text/html')) return response;

  const transformed = transformIndex(await response.text());
  const headers = new Headers(response.headers);
  headers.delete('content-length');
  const result = new Response(transformed, {
    status: response.status,
    statusText: response.statusText,
    headers
  });

  const copy = result.clone();
  caches.open(CACHE).then(cache => cache.put('./index.html', copy));
  return result;
}

self.addEventListener('install', event => event.waitUntil(
  caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())
));

self.addEventListener('activate', event => event.waitUntil(
  caches.keys()
    .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
    .then(() => self.clients.claim())
));

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  // Never proxy or cache XCFind, live-data, map-library, or map-tile requests.
  // Emergency-facing data and mapping resources must use upstream freshness.
  if (url.origin !== self.location.origin) return;

  // Navigation is network-first and applies the focused production workflow
  // update without changing any other page content or behavior.
  if (request.mode === 'navigate') {
    event.respondWith(
      transformedNavigationResponse(request)
        .catch(async () => {
          const cached = await caches.match('./index.html');
          if (!cached) throw new Error('Sky Finder shell unavailable');
          const transformed = transformIndex(await cached.text());
          return new Response(transformed, {
            status: cached.status,
            statusText: cached.statusText,
            headers: cached.headers
          });
        })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) return cached;
      return fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});