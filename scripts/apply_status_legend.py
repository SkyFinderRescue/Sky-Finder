from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
index_path = ROOT / 'index.html'
sw_path = ROOT / 'sw.js'
validate_path = ROOT / 'scripts' / 'validate.py'
e2e_path = ROOT / 'scripts' / 'ui_e2e.mjs'

html = index_path.read_text()

if 'id="pilotStatusLegend"' not in html:
    css = r'''
    /* Firefighter-readable pilot status legend — clean paraglider silhouette, no lower V/pin shape. */
    .statusLegend{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;padding:10px;border-top:1px solid var(--ui-line);background:#0a1628}.legendItem{display:grid;grid-template-columns:42px minmax(0,1fr);gap:8px;align-items:center;min-width:0;padding:8px 9px;border:1px solid rgba(255,255,255,.10);border-radius:12px;background:rgba(255,255,255,.035)}.legendPg{display:block;width:40px;height:40px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.28))}.legendPg .legendCanopy{fill:var(--legend-color);stroke:#fff;stroke-width:1.2}.legendPg .legendLines{fill:none;stroke:var(--legend-color);stroke-width:1.45;stroke-linecap:round}.legendPg .legendPilot{fill:var(--legend-color)}.legendItem.help{--legend-color:#e5484d}.legendItem.recent{--legend-color:#ff6a16}.legendItem.aging{--legend-color:#f4b326}.legendItem.stale{--legend-color:#8998aa}.legendText{min-width:0}.legendText strong{display:block;color:#fff;font-size:11px;line-height:1.18;letter-spacing:.025em}.legendText span{display:block;margin-top:3px;color:var(--ui-muted);font-size:9px;line-height:1.25}.legendItem.help strong{color:#ffb9bd}
    @media(max-width:760px){.statusLegend{grid-template-columns:1fr 1fr;gap:6px;padding:8px}.legendItem{grid-template-columns:36px minmax(0,1fr);gap:6px;padding:7px}.legendPg{width:34px;height:34px}.legendText strong{font-size:10px}.legendText span{font-size:8.5px}}
'''
    style_end = '  </style>'
    if style_end not in html:
        raise RuntimeError('style closing tag not found')
    html = html.replace(style_end, css + '\n' + style_end, 1)

    icon = '''<svg class="legendPg" viewBox="0 0 44 44" aria-hidden="true"><path class="legendCanopy" d="M5 18C9 6 31 3 39 17c2 4 0 7-3 8-2 1-4 0-6-2-6-7-15-7-21 0-2 2-5 3-7 1-2-1-1-4 3-6z"/><path class="legendLines" d="M8 21l12 12M16 18l6 15M24 18l0 15M32 21l-6 12"/><circle class="legendPilot" cx="23" cy="34" r="2.5"/><path class="legendLines" d="M23 36l-3 5m3-5l5 4"/></svg>'''
    legend = f'''        <div id="pilotStatusLegend" class="statusLegend" aria-label="Pilot status legend">
          <div class="legendItem help">{icon}<div class="legendText"><strong>HELP REQUEST</strong><span>Pilot/device requesting help</span></div></div>
          <div class="legendItem recent">{icon}<div class="legendText"><strong>RECENT TRACK POINT</strong><span>Last track point within 2 hrs</span></div></div>
          <div class="legendItem aging">{icon}<div class="legendText"><strong>AGING TRACK POINT</strong><span>Last track point 2–12 hrs old</span></div></div>
          <div class="legendItem stale">{icon}<div class="legendText"><strong>STALE TRACK POINT</strong><span>Last track point over 12 hrs old</span></div></div>
        </div>
'''
    nav_marker = '      <section class="card navigationCard"'
    nav_pos = html.find(nav_marker)
    if nav_pos < 0:
        raise RuntimeError('navigation card marker not found')
    section_end = html.rfind('      </section>', 0, nav_pos)
    if section_end < 0:
        raise RuntimeError('map card closing section not found')
    html = html[:section_end] + legend + html[section_end:]
    index_path.write_text(html)

sw = sw_path.read_text()
sw = re.sub(r'sky-finder-v1\.4\.\d+', 'sky-finder-v1.4.15', sw, count=1)
sw_path.write_text(sw)

validate = validate_path.read_text()
validate = re.sub(r'sky-finder-v1\.4\.\d+', 'sky-finder-v1.4.15', validate)
marker = '# Pilot status legend guardrails'
if marker not in validate:
    validate += r'''

# Pilot status legend guardrails
assert 'id="pilotStatusLegend"' in html, 'Pilot status legend missing'
legend_start = html.index('id="pilotStatusLegend"')
legend_end = html.index('      </section>', legend_start)
legend_html = html[legend_start:legend_end]
for text in [
    'HELP REQUEST', 'Pilot/device requesting help',
    'RECENT TRACK POINT', 'Last track point within 2 hrs',
    'AGING TRACK POINT', 'Last track point 2–12 hrs old',
    'STALE TRACK POINT', 'Last track point over 12 hrs old',
]:
    assert text in legend_html, f'Missing legend text: {text}'
assert legend_html.index('HELP REQUEST') < legend_html.index('RECENT TRACK POINT') < legend_html.index('AGING TRACK POINT') < legend_html.index('STALE TRACK POINT'), 'Legend order must be HELP, recent, aging, stale'
assert legend_html.count('class="legendPg"') == 4, 'Legend must use four paraglider icons'
assert 'legendCanopy' in legend_html and 'legendLines' in legend_html and 'legendPilot' in legend_html, 'Legend paraglider silhouette incomplete'
assert 'map-pin' not in legend_html.lower(), 'Legend must not contain a map-pin/V shape'
print('Sky Finder pilot status legend checks: PASS')
'''
validate_path.write_text(validate)

e2e = e2e_path.read_text()
needle = "  assert.ok(await page.locator('.pilotParaglider').count()>0,'Paraglider markers are missing');"
if 'Pilot status legend is missing' not in e2e:
    addition = """
  assert.ok(await page.locator('#pilotStatusLegend').isVisible(),'Pilot status legend is missing');
  assert.equal(await page.locator('#pilotStatusLegend .legendItem').count(),4,'Pilot status legend must have four items');
  const legendLabels=await page.locator('#pilotStatusLegend .legendText strong').allTextContents();
  assert.deepEqual(legendLabels.map(x=>x.trim()),['HELP REQUEST','RECENT TRACK POINT','AGING TRACK POINT','STALE TRACK POINT'],'Pilot status legend order/text is wrong');
  assert.equal(await page.locator('#pilotStatusLegend .legendPg').count(),4,'Pilot status legend paraglider icons are missing');
"""
    if needle not in e2e:
        raise RuntimeError('E2E insertion point not found')
    e2e = e2e.replace(needle, needle + addition, 1)
e2e_path.write_text(e2e)

print('Sky Finder status legend patch applied')
