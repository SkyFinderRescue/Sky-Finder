from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'
SW = ROOT / 'sw.js'
VALIDATE = ROOT / 'scripts' / 'validate.py'

html = INDEX.read_text()

def replace_once(old: str, new: str) -> None:
    global html
    count = html.count(old)
    if count != 1:
        raise RuntimeError(f'Expected one match, found {count}: {old[:120]!r}')
    html = html.replace(old, new, 1)

replace_once(
    '.btn.smallBtn{min-height:38px;padding:8px 10px;font-size:12px}.btn:disabled{opacity:.5;cursor:not-allowed}',
    '.btn.smallBtn{min-height:38px;padding:8px 10px;font-size:12px}.btn:disabled{opacity:.5;cursor:not-allowed}.btn[aria-disabled="true"]{opacity:.45;pointer-events:none;filter:saturate(.35)}'
)

replace_once(
    "function updateMarkerStyles(){const byId=new Map(allPilots().map(p=>[pilotId(p),p]));markerByPilotId.forEach((m,id)=>{const p=byId.get(id);if(p&&m.setStyle){m.setStyle(markerStyle(p));if(m.setRadius)m.setRadius(selectedPilotIds.has(id)?10:7)}})}",
    "function updateMarkerStyles(){const byId=new Map(allPilots().map(p=>[pilotId(p),p]));markerByPilotId.forEach((m,id)=>{const p=byId.get(id);if(p&&m.setStyle){m.setStyle(markerStyle(p));if(m.setRadius)m.setRadius(selectedPilotIds.has(id)?10:7)}})} function setPilotAsTarget(id){const p=allPilots().find(x=>pilotId(x)===id);if(!p)return;const lat=Number(p.lat),lng=Number(p.lng);if(!Number.isFinite(lat)||!Number.isFinite(lng))return;els.targetCoords.value=`${fmt(lat)}, ${fmt(lng)}`;updateTarget();els.targetStatus.textContent=`${p.name||'Pilot'}: ${coordText({lat,lng})}`;}"
)

replace_once(
    "function togglePilotSelection(id){if(!id)return;selectedPilotIds.has(id)?selectedPilotIds.delete(id):selectedPilotIds.add(id);renderSelectionState()} function selectOnlyPilot(id,center=true){selectedPilotIds.clear();if(id)selectedPilotIds.add(id);if(center&&id&&map){const p=allPilots().find(x=>pilotId(x)===id);if(p)map.setView([Number(p.lat),Number(p.lng)],Math.max(map.getZoom?map.getZoom():10,11))}renderSelectionState()} function clearPilotSelection(){selectedPilotIds.clear();renderSelectionState()}",
    "function togglePilotSelection(id){if(!id)return;if(selectedPilotIds.has(id)){selectedPilotIds.delete(id)}else{selectedPilotIds.add(id);setPilotAsTarget(id)}renderSelectionState()} function selectOnlyPilot(id,center=true){selectedPilotIds.clear();if(id){selectedPilotIds.add(id);setPilotAsTarget(id)}if(center&&id&&map){const p=allPilots().find(x=>pilotId(x)===id);if(p)map.setView([Number(p.lat),Number(p.lng)],Math.max(map.getZoom?map.getZoom():10,11))}renderSelectionState()} function clearPilotSelection(){selectedPilotIds.clear();renderSelectionState()}"
)

replace_once(
    "function setTargetLinks(p){const q=`${p.lat},${p.lng}`,links={apple:`https://maps.apple.com/?daddr=${encodeURIComponent(q)}&dirflg=d`,google:`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(q)}`,w3w:`https://what3words.com/?map=${encodeURIComponent(`${p.lat},${p.lng},17`)}`};",
    "function setTargetLinks(p){const q=`${p.lat},${p.lng}`,links={apple:`https://maps.apple.com/?daddr=${encodeURIComponent(q)}&dirflg=d`,google:`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(q)}`,w3w:'https://map.what3words.com/'};"
)

replace_once('>what3words</a>', '>W3W Search</a>')

replace_once(
    "els.mapPilotList.addEventListener('change',e=>{const box=e.target.closest?e.target.closest('.mapPilotCheck'):null;if(!box)return;box.checked?selectedPilotIds.add(box.dataset.pilotId):selectedPilotIds.delete(box.dataset.pilotId);renderSelectionState()});",
    "els.mapPilotList.addEventListener('change',e=>{const box=e.target.closest?e.target.closest('.mapPilotCheck'):null;if(!box)return;if(box.checked){selectedPilotIds.add(box.dataset.pilotId);setPilotAsTarget(box.dataset.pilotId)}else selectedPilotIds.delete(box.dataset.pilotId);renderSelectionState()});"
)

replace_once(
    "[els.appleTarget,els.googleTarget,els.w3wTarget].forEach(a=>a.addEventListener('click',e=>{if(!targetPosition)e.preventDefault()}));",
    "[els.appleTarget,els.googleTarget].forEach(a=>a.addEventListener('click',e=>{if(!targetPosition)e.preventDefault()}));els.w3wTarget.addEventListener('click',e=>{if(!targetPosition){e.preventDefault();return}const coords=coordText(targetPosition);void copyText(coords,'Copied for what3words');els.targetStatus.textContent=`what3words: copied ${coords}. Paste into Search.`;});"
)

INDEX.write_text(html)

sw = SW.read_text()
if sw.count('sky-finder-v1.3.0') != 1:
    raise RuntimeError('Unexpected service worker version')
SW.write_text(sw.replace('sky-finder-v1.3.0', 'sky-finder-v1.4.0', 1))

validate = VALIDATE.read_text()
validate = validate.replace('assert "sky-finder-v1.3.0" in sw', 'assert "sky-finder-v1.4.0" in sw', 1)
needle = '    "gpsActions",\n'
if needle not in validate:
    raise RuntimeError('Validator anchor missing')
validate = validate.replace(needle, needle + '    "setPilotAsTarget",\n    "https://map.what3words.com/",\n    "Copied for what3words",\n', 1)
validate += '\nassert "https://what3words.com/?map=" not in html, "Unsafe legacy what3words coordinate URL is still present"\n'
VALIDATE.write_text(validate)

print('what3words target fix applied')
