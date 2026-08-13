from pathlib import Path

p=Path('index.html')
html=p.read_text()

modal_css="""
    body.w3wOpen{overflow:hidden}.w3wModal{position:fixed;inset:0;z-index:5000;background:rgba(2,8,18,.88);display:flex;align-items:center;justify-content:center;padding:max(10px,env(safe-area-inset-top)) max(10px,env(safe-area-inset-right)) max(10px,env(safe-area-inset-bottom)) max(10px,env(safe-area-inset-left));backdrop-filter:blur(8px)}.w3wModal[hidden]{display:none}.w3wDialog{width:min(980px,100%);height:min(900px,92vh);background:#fff;border-radius:18px;overflow:hidden;display:grid;grid-template-rows:auto 1fr;box-shadow:0 24px 90px rgba(0,0,0,.55)}.w3wModalHead{display:flex;align-items:center;justify-content:space-between;gap:10px;background:#08111f;color:#fff;padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.14)}.w3wModalTitle{font-size:14px;font-weight:850;line-height:1.25}.w3wModalCoords{font-size:10px;color:#becbe2;margin-top:2px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}.w3wFrame{display:block;width:100%;height:100%;border:0;background:#fff}.w3wClose{min-height:38px;white-space:nowrap}@media(max-width:650px){.w3wModal{padding:max(4px,env(safe-area-inset-top)) max(4px,env(safe-area-inset-right)) max(4px,env(safe-area-inset-bottom)) max(4px,env(safe-area-inset-left))}.w3wDialog{height:96vh;border-radius:12px}.w3wModalHead{padding:7px 8px}.w3wModalTitle{font-size:12px}.w3wClose{min-height:34px;padding:6px 9px;font-size:11px}}
"""
if 'class="w3wModal"' not in html:
    html=html.replace('</style>',modal_css+'  </style>',1)

old='<a id="w3wTarget" class="btn" href="#" target="_blank" rel="noopener noreferrer" aria-disabled="true" title="Open selected pilot coordinates directly in what3words">W3W</a>'
new='<button id="w3wTarget" class="btn" type="button" disabled title="Open selected pilot in what3words">W3W</button>'
assert old in html, 'current W3W button markup not found'
html=html.replace(old,new,1)

modal="""    <div id="w3wModal" class="w3wModal" hidden role="dialog" aria-modal="true" aria-labelledby="w3wModalTitle">
      <div class="w3wDialog">
        <div class="w3wModalHead"><div><div id="w3wModalTitle" class="w3wModalTitle">what3words — pilot location</div><div id="w3wModalCoords" class="w3wModalCoords"></div></div><button id="w3wCloseBtn" class="btn w3wClose" type="button">Close</button></div>
        <iframe id="w3wFrame" class="w3wFrame" title="what3words map for selected pilot" loading="eager" referrerpolicy="no-referrer" allow="geolocation 'none'; fullscreen"></iframe>
      </div>
    </div>
"""
footer='    <div class="footer">'
assert footer in html, 'footer insertion point not found'
html=html.replace(footer,modal+footer,1)

old_els="w3wTarget:$('w3wTarget'),copyTargetBtn:$('copyTargetBtn')};"
new_els="w3wTarget:$('w3wTarget'),copyTargetBtn:$('copyTargetBtn'),w3wModal:$('w3wModal'),w3wFrame:$('w3wFrame'),w3wModalTitle:$('w3wModalTitle'),w3wModalCoords:$('w3wModalCoords'),w3wCloseBtn:$('w3wCloseBtn')};"
assert old_els in html, 'elements map insertion point not found'
html=html.replace(old_els,new_els,1)

old_links="function setTargetLinks(p){const q=`${p.lat},${p.lng}`,links={apple:`https://maps.apple.com/?daddr=${encodeURIComponent(q)}&dirflg=d`,google:`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(q)}`};[[els.appleTarget,links.apple],[els.googleTarget,links.google]].forEach(([a,href])=>{a.href=href;a.removeAttribute('aria-disabled')});els.w3wTarget.href='#';els.w3wTarget.dataset.safeCopy='true';els.w3wTarget.textContent='W3W Copy';els.w3wTarget.title='Copy selected pilot coordinates for what3words';els.w3wTarget.removeAttribute('aria-disabled');els.copyTargetBtn.disabled=false} function clearTargetLinks(){[els.appleTarget,els.googleTarget,els.w3wTarget].forEach(a=>{a.href='#';a.setAttribute('aria-disabled','true')});delete els.w3wTarget.dataset.safeCopy;els.w3wTarget.textContent='W3W';els.copyTargetBtn.disabled=true}"
new_links="function w3wCoordinateUrl(p){return `https://what3words.com/${encodeURIComponent(`${p.lat},${p.lng}`)}`} function openW3wModal(p){if(!p)return;const pilot=activePilotId?allPilots().find(x=>pilotId(x)===activePilotId):null;els.w3wModalTitle.textContent=pilot?`what3words — ${pilot.name||'Pilot'}`:'what3words — pilot location';els.w3wModalCoords.textContent=coordText(p);els.w3wFrame.src=w3wCoordinateUrl(p);els.w3wModal.hidden=false;document.body.classList.add('w3wOpen')} function closeW3wModal(){els.w3wModal.hidden=true;els.w3wFrame.src='about:blank';document.body.classList.remove('w3wOpen')} function setTargetLinks(p){const q=`${p.lat},${p.lng}`,links={apple:`https://maps.apple.com/?daddr=${encodeURIComponent(q)}&dirflg=d`,google:`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(q)}`};[[els.appleTarget,links.apple],[els.googleTarget,links.google]].forEach(([a,href])=>{a.href=href;a.removeAttribute('aria-disabled')});els.w3wTarget.disabled=false;els.w3wTarget.title='Open selected pilot in embedded what3words web map';els.copyTargetBtn.disabled=false} function clearTargetLinks(){[els.appleTarget,els.googleTarget].forEach(a=>{a.href='#';a.setAttribute('aria-disabled','true')});els.w3wTarget.disabled=true;els.copyTargetBtn.disabled=true}"
assert old_links in html, 'current W3W setTargetLinks implementation not found'
html=html.replace(old_links,new_links,1)

old_handler="els.w3wTarget.addEventListener('click',async e=>{if(els.w3wTarget.dataset.safeCopy!=='true')return;e.preventDefault();if(!targetPosition)return;const coords=coordText(targetPosition),old=els.w3wTarget.textContent;els.w3wTarget.textContent=await copyText(coords,'Copied');els.targetStatus.className='status warn';els.targetStatus.textContent=`what3words direct mobile handoff unavailable. Copied selected pilot coordinates ${coords}; paste into what3words Search.`;setTimeout(()=>els.w3wTarget.textContent=old,1400)});"
new_handler="els.w3wTarget.addEventListener('click',()=>{if(targetPosition)openW3wModal(targetPosition)});els.w3wCloseBtn.addEventListener('click',closeW3wModal);els.w3wModal.addEventListener('click',e=>{if(e.target===els.w3wModal)closeW3wModal()});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!els.w3wModal.hidden)closeW3wModal()});"
assert old_handler in html, 'current W3W safe-copy click handler not found'
html=html.replace(old_handler,new_handler,1)
p.write_text(html)

v=Path('scripts/validate.py')
text=v.read_text()
text=text.replace('    "dataset.safeCopy",\n    "W3W Copy",\n','    "w3wModal",\n    "w3wFrame",\n    "w3wCoordinateUrl",\n    "geolocation \'none\'",\n',1)
text=text.replace('assert "sky-finder-v1.4.10" in sw','assert "sky-finder-v1.4.11" in sw',1)
old_checks='''assert "https://what3words.com/?map=" not in html, "Broken legacy what3words map handoff remains"\nassert "https://map.what3words.com/${p.lat},${p.lng}" not in html, "Unreliable coordinate-path W3W handoff remains"\nassert "dataset.safeCopy" in html, "Safe W3W coordinate-copy fallback missing"\nassert "W3W Copy" in html, "Safe W3W button label missing"\n'''
new_checks='''assert "https://what3words.com/?map=" not in html, "Broken legacy what3words map handoff remains"\nassert "https://map.what3words.com/${p.lat},${p.lng}" not in html, "Unreliable top-level coordinate-path W3W handoff remains"\nassert "dataset.safeCopy" not in html, "Obsolete W3W copy/paste fallback remains"\nassert "W3W Copy" not in html, "Obsolete W3W copy button remains"\nassert "function w3wCoordinateUrl(p)" in html, "Embedded W3W coordinate URL builder missing"\nassert "allow=\\\"geolocation 'none'; fullscreen\\\"" in html, "Embedded W3W must not receive responder geolocation"\nassert "els.w3wFrame.src=w3wCoordinateUrl(p)" in html, "W3W modal must use selected pilot coordinates"\nassert "els.w3wFrame.src='about:blank'" in html, "W3W modal must unload on close"\n'''
assert old_checks in text, 'old W3W validation checks not found'
text=text.replace(old_checks,new_checks,1)
v.write_text(text)

sw=Path('sw.js')
s=sw.read_text().replace('sky-finder-v1.4.10','sky-finder-v1.4.11',1)
sw.write_text(s)
