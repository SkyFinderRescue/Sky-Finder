from pathlib import Path
import re

p=Path('index.html')
html=p.read_text()

# 1) New visual system, layout, large map, and approved logo.
css='''
    /* Sky Finder UI refresh — visual/layout only. Core rescue behavior remains unchanged. */
    :root{--ui-bg:#f4f7fb;--ui-card:#ffffff;--ui-navy:#0b2442;--ui-navy2:#07192e;--ui-orange:#ff4a16;--ui-line:#d9e2ec;--ui-text:#11243c;--ui-muted:#61738a;--ui-green:#16884b;--ui-shadow:0 8px 24px rgba(7,25,46,.08)}
    body{background:var(--ui-bg);color:var(--ui-text)}
    .app{max-width:1120px;padding:18px 18px 28px}
    .topbar{background:transparent;margin-bottom:12px;align-items:center}.brandLockup{gap:12px}.brandLogo{width:min(440px,58vw);height:auto;max-height:86px;border-radius:0;background:transparent;object-fit:contain;box-shadow:none}.brand{display:none}.live{background:#fff;color:var(--ui-navy);border-color:#dfe7f0;box-shadow:var(--ui-shadow)}
    .layout{display:grid;grid-template-columns:minmax(0,1fr);gap:12px}.card{background:var(--ui-card);border:1px solid var(--ui-line);border-radius:18px;box-shadow:var(--ui-shadow);overflow:hidden}.cardHead{background:#fff;border-bottom:1px solid var(--ui-line);padding:10px 14px}.cardHead h2{color:var(--ui-navy)}
    .mapCard .cardHead{display:none}.mapCard .cardBody{display:none}.mapStage{display:grid;grid-template-columns:1fr;grid-template-rows:minmax(410px,58vh) auto;height:auto;min-height:500px;background:#fff}.mapCanvasWrap{order:1;min-height:410px}.mapRoster{order:2;border:0;border-top:1px solid var(--ui-line);background:#fff}.mapRosterHead{padding:10px 14px}.mapRosterTitle{font-size:13px;color:var(--ui-navy)}.mapRosterMeta{font-size:11px;color:var(--ui-muted)}.mapPilotList{padding:7px 10px 11px;display:flex;gap:7px;overflow-x:auto}.mapPilotRow{min-width:max-content;border:1px solid #dce5ef;background:#f8fafc;color:var(--ui-text);border-radius:12px;padding:7px 10px}.mapPilotRow.selected{border-color:var(--ui-orange);background:#fff3ee}.mapPilotName{font-size:13px;color:var(--ui-navy)}.mapPilotMeta{color:var(--ui-muted)}
    .mapSelection{background:rgba(7,25,46,.92);border:0;border-radius:11px;color:#fff}.mapOverlay .btn{background:#fff;color:var(--ui-navy);border-color:#fff;box-shadow:0 3px 12px rgba(7,25,46,.18)}.mapOverlay .primary{background:var(--ui-navy);color:#fff;border-color:var(--ui-navy)}
    .navigationCard{order:2}.navigationCard .cardHead{display:flex}.navigationCard .cardBody{padding:14px}.navigationCard .section{padding:0;margin:0}.navigationCard .section h3{display:none}.targetLinks{grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.targetLinks .btn{min-height:52px;border-radius:13px;font-weight:800}.targetLinks .good{background:#fff;color:var(--ui-navy);border:1px solid #bfcddd}.targetLinks #w3wTarget{background:#fff;color:var(--ui-navy);border:1px solid #bfcddd}.targetLinks #copyTargetBtn{background:#fff;color:var(--ui-navy);border:1px solid #bfcddd}.metric{background:#f7fafc;border-color:#d9e3ed}.metric .k{color:var(--ui-muted)}.metric .v{color:var(--ui-navy)}
    .toolsCard{order:3}.toolsCard .cardHead{display:none}.toolsCard .cardBody{padding:0}.toolsCard .section{padding:14px;margin:0;border-top:1px solid var(--ui-line)}.toolsCard .section:first-child{border-top:0}.toolsCard .section h3{color:var(--ui-navy)}.gpsActions .primary{background:var(--ui-orange);border-color:var(--ui-orange)}
    .pilotSearchRow input,.navigationCard input{background:#f8fafc;color:var(--ui-text);border-color:#cfdae6}.pilotCard{background:#fff;border-color:#dce5ef;color:var(--ui-text);box-shadow:none}.pilotCard.selected{background:#fff7f3;border-color:var(--ui-orange)}.pilotName,.pilotCoords{color:var(--ui-navy)}.pilotMeta,.small,.filterLine{color:var(--ui-muted)}.verifyPilotBtn{background:var(--ui-navy);color:#fff;border-color:var(--ui-navy)}
    .footer{color:var(--ui-muted)}.footer a{color:var(--ui-navy)}
    .pilotParaglider{background:transparent!important;border:0!important}.pilotParaglider .pgWrap{width:44px;height:44px;transform-origin:center bottom;filter:drop-shadow(0 3px 4px rgba(0,0,0,.24));transition:transform .12s ease}.pilotParaglider.selected .pgWrap{transform:scale(1.22)}.pilotParaglider svg{display:block;width:44px;height:44px}.pilotParaglider .pgCanopy{fill:#ff4a16;stroke:#fff;stroke-width:1.8}.pilotParaglider.stale .pgCanopy{fill:#8998aa}.pilotParaglider.warn .pgCanopy{fill:#f4b326}.pilotParaglider.help .pgCanopy{fill:#e5484d}.pilotParaglider .pgLines{stroke:#0b2442;stroke-width:1.2}.pilotParaglider .pgPilot{fill:#0b2442}.pilotParaglider.selected .pgCanopy{fill:#ff5a1f;stroke:#0b2442;stroke-width:2.4}
    .w3wDialog{box-shadow:0 24px 90px rgba(0,0,0,.45)}
    @media(max-width:650px){.app{padding:8px 8px 18px}.topbar{margin-bottom:8px}.brandLogo{width:min(330px,75vw);max-height:64px}.live{font-size:10px;padding:5px 8px}.card{border-radius:15px}.mapStage{grid-template-rows:minmax(390px,56vh) auto;min-height:470px}.mapCanvasWrap{min-height:390px}.mapPilotList{padding:6px 7px 9px}.navigationCard .cardBody{padding:10px}.targetLinks{grid-template-columns:1fr 1fr;gap:7px}.targetLinks .btn{min-height:48px}.toolsCard .section{padding:11px 10px}.pilotList{max-height:330px}.footer{padding-bottom:6px}.pilotParaglider .pgWrap,.pilotParaglider svg{width:40px;height:40px}}
'''
html=html.replace('</style>',css+'  </style>',1)

# 2) Header: approved wordmark SVG. Keep status indicator untouched.
html=re.sub(r'<div class="brandLockup">.*?</div>\s*<div class="live"', '<div class="brandLockup"><img class="brandLogo" src="./assets/brand-logo.svg" alt="Sky Finder — Paraglider Rescue Locator" /></div><div class="live"', html, count=1, flags=re.S)

# 3) Mark cards for CSS ordering and remove redundant map title/note without removing controls.
html=html.replace('<section class="card" aria-labelledby="pilotMapTitle">','<section class="card mapCard" aria-labelledby="pilotMapTitle">',1)
html=html.replace('<aside class="card" aria-labelledby="rescueToolsTitle">','<aside class="card toolsCard" aria-labelledby="rescueToolsTitle">',1)
html=html.replace('<div class="cardBody"><div class="note"><strong>Field use:</strong> Tap a pilot or marker to select. Verify timestamp in XCFind.</div></div>','',1)

# 4) Move the existing Navigation section out of Rescue Tools and directly under the map.
nav_match=re.search(r'<section class="section"><h3>Navigation</h3>.*?</section>', html, flags=re.S)
if not nav_match:
    raise SystemExit('Navigation section not found')
nav_section=nav_match.group(0)
html=html[:nav_match.start()]+html[nav_match.end():]
nav_card='<section class="card navigationCard" aria-labelledby="navigationTitle"><div class="cardHead"><h2 id="navigationTitle">Navigation</h2></div><div class="cardBody">'+nav_section+'</div></section>'
map_end='      </section>\n      <aside class="card toolsCard"'
if map_end not in html:
    raise SystemExit('Map/tools boundary not found')
html=html.replace(map_end,'      </section>\n      '+nav_card+'\n      <aside class="card toolsCard"',1)

# 5) Replace circle markers with paraglider icons while preserving click/select behavior.
old_sync="function syncMapMarkers(){if(!map||!window.L)return;markerByPilotId.forEach(m=>m.remove());markerByPilotId.clear();allPilots().forEach(p=>{const id=pilotId(p),m=L.circleMarker([Number(p.lat),Number(p.lng)],markerStyle(p)).addTo(map);m.bindTooltip(escapeHtml(p.name||'Unnamed pilot'),{direction:'top',opacity:.95});m.on('click',()=>togglePilotSelection(id));markerByPilotId.set(id,m)});updateMarkerStyles();renderMapRoster();renderPilots();updateFilterText()}"
if old_sync not in html:
    raise SystemExit('syncMapMarkers implementation not found')
new_sync="function pilotMarkerIcon(p,id){const selected=selectedPilotIds.has(id),age=pointAgeHours(p),status=String(p.type)==='3'?'help':age<=2?'fresh':age<=12?'warn':'stale';const svg=`<div class=\"pgWrap\"><svg viewBox=\"0 0 44 44\" aria-hidden=\"true\"><path class=\"pgCanopy\" d=\"M5 18C9 6 31 3 39 17c2 4 0 7-3 8-2 1-4 0-6-2-6-7-15-7-21 0-2 2-5 3-7 1-2-1-1-4 3-6z\"/><path class=\"pgLines\" d=\"M8 21l12 12M16 18l6 15M24 18l0 15M32 21l-6 12\"/><circle class=\"pgPilot\" cx=\"23\" cy=\"34\" r=\"2.5\"/><path class=\"pgLines\" d=\"M23 36l-3 5m3-5l5 4\"/></svg></div>`;return L.divIcon({className:`pilotParaglider ${status}${selected?' selected':''}`,html:svg,iconSize:[44,44],iconAnchor:[22,41],tooltipAnchor:[0,-32]})} function syncMapMarkers(){if(!map||!window.L)return;markerByPilotId.forEach(m=>m.remove());markerByPilotId.clear();allPilots().forEach(p=>{const id=pilotId(p),m=L.marker([Number(p.lat),Number(p.lng)],{icon:pilotMarkerIcon(p,id),keyboard:true,title:String(p.name||'Unnamed pilot')}).addTo(map);m.bindTooltip(escapeHtml(p.name||'Unnamed pilot'),{direction:'top',opacity:.95});m.on('click',()=>togglePilotSelection(id));markerByPilotId.set(id,m)});updateMarkerStyles();renderMapRoster();renderPilots();updateFilterText()}"
html=html.replace(old_sync,new_sync,1)

old_update="function updateMarkerStyles(){const byId=new Map(allPilots().map(p=>[pilotId(p),p]));markerByPilotId.forEach((m,id)=>{const p=byId.get(id);if(p&&m.setStyle){m.setStyle(markerStyle(p));if(m.setRadius)m.setRadius(selectedPilotIds.has(id)?10:7)}})}"
if old_update not in html:
    raise SystemExit('updateMarkerStyles implementation not found')
new_update="function updateMarkerStyles(){const byId=new Map(allPilots().map(p=>[pilotId(p),p]));markerByPilotId.forEach((m,id)=>{const p=byId.get(id);if(p&&m.setIcon)m.setIcon(pilotMarkerIcon(p,id))})}"
html=html.replace(old_update,new_update,1)

# 6) Keep service-worker cache moving forward for UI asset refresh.
p.write_text(html)

sw=Path('sw.js')
s=sw.read_text()
m=re.search(r"sky-finder-v(\d+)\.(\d+)\.(\d+)",s)
if not m: raise SystemExit('service worker version not found')
major,minor,patch=map(int,m.groups())
newver=f'sky-finder-v{major}.{minor}.{patch+1}'
s=s[:m.start()]+newver+s[m.end():]
sw.write_text(s)

# Ensure new logo participates in shell cache.
s=sw.read_text()
if "'./assets/brand-logo.svg'" not in s:
    s=s.replace("'./assets/icon.svg'", "'./assets/icon.svg','./assets/brand-logo.svg'",1)
    sw.write_text(s)

# Update validation version and UI requirements while retaining all functional checks.
v=Path('scripts/validate.py')
t=v.read_text()
t=re.sub(r'assert "sky-finder-v\d+\.\d+\.\d+" in sw', f'assert "{newver}" in sw', t, count=1)
t=t.replace('    "Pilot Area Map",\n','',1)
t=t.replace('    "gpsActions",\n','    "gpsActions",\n    "assets/brand-logo.svg",\n    "navigationCard",\n    "pilotMarkerIcon",\n',1)
t += '''\n# UI-only redesign guardrails\nassert 'class="card mapCard"' in html\nassert 'class="card navigationCard"' in html\nassert html.index('class="card mapCard"') < html.index('class="card navigationCard"') < html.index('class="card toolsCard"')\nassert 'Pilot Area Map' not in html, 'Redundant Pilot Area Map label remains'\nassert 'Verify timestamp in XCFind.' not in html, 'Redundant timestamp instruction remains'\nassert 'L.marker([Number(p.lat),Number(p.lng)]' in html, 'Paraglider map marker implementation missing'\nassert 'pilotParaglider' in html and 'pgCanopy' in html, 'Paraglider marker visual missing'\nassert 'minmax(390px,56vh)' in html, 'Mobile map minimum height guard missing'\nassert './assets/brand-logo.svg' in html, 'Approved brand logo missing from header'\nassert "'./assets/brand-logo.svg'" in sw, 'Approved brand logo missing from service-worker shell'\nprint('Sky Finder UI redesign checks: PASS')\n'''
v.write_text(t)
print('Applied Sky Finder UI redesign; service worker ->',newver)
