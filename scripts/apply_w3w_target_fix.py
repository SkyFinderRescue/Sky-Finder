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
        raise RuntimeError(f'Expected one match, found {count}: {old[:140]!r}')
    html = html.replace(old, new, 1)


def replace_between(start: str, end: str, replacement: str) -> None:
    global html
    i = html.find(start)
    if i < 0:
        raise RuntimeError(f'Start anchor missing: {start!r}')
    j = html.find(end, i + len(start))
    if j < 0:
        raise RuntimeError(f'End anchor missing after {start!r}: {end!r}')
    html = html[:i] + replacement + html[j:]


# Make anchor-style navigation buttons clearly inactive until a target exists.
replace_once(
    '.btn.smallBtn{min-height:38px;padding:8px 10px;font-size:12px}.btn:disabled{opacity:.5;cursor:not-allowed}',
    '.btn.smallBtn{min-height:38px;padding:8px 10px;font-size:12px}.btn:disabled{opacity:.5;cursor:not-allowed}.btn[aria-disabled="true"]{opacity:.45;pointer-events:none;filter:saturate(.35)}'
)

# Add one canonical way to turn a pilot selection into the Navigation target.
marker_start = 'function updateMarkerStyles(){'
marker_end = ' function togglePilotSelection'
i = html.find(marker_start)
j = html.find(marker_end, i)
if i < 0 or j < 0:
    raise RuntimeError('Could not locate updateMarkerStyles block')
marker_block = html[i:j]
if 'setPilotAsTarget' not in marker_block:
    helper = " function setPilotAsTarget(id){const p=allPilots().find(x=>pilotId(x)===id);if(!p)return;const lat=Number(p.lat),lng=Number(p.lng);if(!Number.isFinite(lat)||!Number.isFinite(lng))return;els.targetCoords.value=`${fmt(lat)}, ${fmt(lng)}`;updateTarget();els.targetStatus.textContent=`${p.name||'Pilot'}: ${coordText({lat,lng})}`;}"
    html = html[:j] + helper + html[j:]

replace_between(
    'function togglePilotSelection(id){',
    ' function selectOnlyPilot',
    "function togglePilotSelection(id){if(!id)return;if(selectedPilotIds.has(id)){selectedPilotIds.delete(id)}else{selectedPilotIds.add(id);setPilotAsTarget(id)}renderSelectionState()}"
)
replace_between(
    'function selectOnlyPilot(id,center=true){',
    ' function clearPilotSelection',
    "function selectOnlyPilot(id,center=true){selectedPilotIds.clear();if(id){selectedPilotIds.add(id);setPilotAsTarget(id)}if(center&&id&&map){const p=allPilots().find(x=>pilotId(x)===id);if(p)map.setView([Number(p.lat),Number(p.lng)],Math.max(map.getZoom?map.getZoom():10,11))}renderSelectionState()}"
)

# Replace the unsupported what3words ?map=lat,lng shortcut. Current what3words
# ignores it on mobile and may fall back to the responder's own GPS position.
replace_between(
    'function setTargetLinks(p){',
    ' function clearTargetLinks',
    "function setTargetLinks(p){const q=`${p.lat},${p.lng}`,links={apple:`https://maps.apple.com/?daddr=${encodeURIComponent(q)}&dirflg=d`,google:`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(q)}`,w3w:'https://map.what3words.com/'};[[els.appleTarget,links.apple],[els.googleTarget,links.google],[els.w3wTarget,links.w3w]].forEach(([a,href])=>{a.href=href;a.removeAttribute('aria-disabled')});els.copyTargetBtn.disabled=false}"
)
replace_once('>what3words</a>', '>W3W Search</a>')

# Selecting a checkbox on the map also becomes the active Navigation target.
replace_between(
    "els.mapPilotList.addEventListener('change'",
    ';els.clearSelectionBtn',
    "els.mapPilotList.addEventListener('change',e=>{const box=e.target.closest?e.target.closest('.mapPilotCheck'):null;if(!box)return;if(box.checked){selectedPilotIds.add(box.dataset.pilotId);setPilotAsTarget(box.dataset.pilotId)}else selectedPilotIds.delete(box.dataset.pilotId);renderSelectionState()})"
)

# Apple/Google continue to use direct coordinate destinations. W3W copies the
# exact selected target and opens its supported search UI rather than silently
# substituting device location.
replace_between(
    "[els.appleTarget,els.googleTarget,els.w3wTarget].forEach",
    ';els.copyTargetBtn.addEventListener',
    "[els.appleTarget,els.googleTarget].forEach(a=>a.addEventListener('click',e=>{if(!targetPosition)e.preventDefault()}));els.w3wTarget.addEventListener('click',e=>{if(!targetPosition){e.preventDefault();return}const coords=coordText(targetPosition);void copyText(coords,'Copied for what3words');els.targetStatus.textContent=`what3words: copied ${coords}. Paste into Search.`;})"
)

INDEX.write_text(html)

sw = SW.read_text()
if sw.count('sky-finder-v1.3.0') != 1:
    raise RuntimeError('Unexpected service worker version')
SW.write_text(sw.replace('sky-finder-v1.3.0', 'sky-finder-v1.4.0', 1))

validate = VALIDATE.read_text()
if validate.count('assert "sky-finder-v1.3.0" in sw') != 1:
    raise RuntimeError('Unexpected validator service-worker version')
validate = validate.replace('assert "sky-finder-v1.3.0" in sw', 'assert "sky-finder-v1.4.0" in sw', 1)
needle = '    "gpsActions",\n'
if needle not in validate:
    raise RuntimeError('Validator anchor missing')
validate = validate.replace(
    needle,
    needle + '    "setPilotAsTarget",\n    "https://map.what3words.com/",\n    "Copied for what3words",\n',
    1,
)
print_anchor = '\nprint("Sky Finder static validation: PASS")'
if print_anchor not in validate:
    raise RuntimeError('Validator print anchor missing')
validate = validate.replace(
    print_anchor,
    '\nassert "https://what3words.com/?map=" not in html, "Unsafe legacy what3words coordinate URL is still present"' + print_anchor,
    1,
)
VALIDATE.write_text(validate)

print('what3words target fix applied')
