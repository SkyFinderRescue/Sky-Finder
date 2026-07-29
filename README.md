# Sky Finder

California paraglider rescue locator built for fast field use.

## Production workflow

- The embedded XCFind California group (`id=16`) remains the authoritative live pilot map.
- A GitHub Actions relay reads XCFind's public 48-hour JSON feed every five minutes and publishes a minimal quick-search snapshot containing only each pilot's latest point.
- Search a pilot by name/call sign, review the last-point age, then select **Use Last Point** to populate the rescue target.
- Sky Finder obtains the responder's device GPS location and calculates straight-line distance and bearing.
- One-tap handoffs are provided for Apple Maps, Google Maps, and what3words.
- Manual coordinate entry remains available as a fallback.
- If the embedded XCFind view is restricted by a browser, **Open Full XCFind** provides a direct fallback.

## Safety design

Sky Finder does not guess the newest pilot position from track-point numbering. The relay chooses the newest message by timestamp, displays snapshot/position age, and does not republish message text, battery state, device IDs, or track history. Verify pilot identity, timestamp, and coordinates in XCFind before committing resources.

## Deployment

The production app is static and designed for GitHub Pages. GPS requires HTTPS. The live quick-search relay publishes its current snapshot to the `data-live` branch.

## Validation

Run:

```bash
python scripts/validate.py
```

Validation checks the production UI, JavaScript/service-worker syntax, PWA assets, live-search controls, and snapshot transformation tests. GitHub Actions also fetches and validates the current XCFind feed before live-data changes can be merged.
