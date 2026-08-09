# Sky Finder

California paraglider rescue locator built for fast field use.

## Production workflow

- XCFind California group (`id=16`) remains the authoritative tracking source.
- A GitHub Actions relay reads XCFind's public 48-hour JSON feed every five minutes and publishes a minimal snapshot containing only each pilot's newest point.
- Sky Finder's primary map plots those recent last-points on an interactive area map. Zoom/pan to an incident area and both pilot lists automatically show only positions inside the visible map.
- The left-side **Pilots in map view** roster supports one or multiple selections. Once any pilot is selected, **Rescue Tools shows selected pilots only** until the selection is cleared.
- Selecting a pilot automatically populates that pilot's newest point as the rescue target. Sky Finder uses responder GPS to calculate straight-line distance and bearing and provides Apple Maps, Google Maps, and what3words handoffs.
- The what3words handoff passes the selected pilot's latitude and longitude in native `latitude,longitude` form so mobile browsers do not receive an encoded comma in the target path.
- Search still works across the full recent XCFind snapshot when no pilot is selected.
- **Open XCFind Tracks** and **Verify in XCFind** remain available for source verification and track history.
- Manual coordinate entry remains available as a fallback.

## Branding

The approved Sky Finder locator/paraglider logo is displayed in the application header and is also used for the browser favicon, Apple touch icon, and installable PWA icon.

## Safety design

Sky Finder does not infer newest position from track-point numbering. The relay chooses the newest message by timestamp. The interface displays snapshot age and each pilot point's age because a recent last-known point is not proof that the pilot is still active at that location. Message text, battery state, device IDs, and track history are not mirrored into the quick snapshot. Verify pilot identity, timestamp, and coordinates in XCFind before committing resources.

## Deployment

The production app is static and designed for GitHub Pages. GPS requires HTTPS. The live snapshot is published to the `data-live` branch. The area map uses Leaflet/OpenStreetMap for visualization and the XCFind snapshot for pilot positions.

## Validation

Run:

```bash
python scripts/validate.py
```

Validation checks the production UI, JavaScript/service-worker syntax, PWA assets, visible logo branding, area-map/selection controls, routing controls, and snapshot transformation tests. GitHub Actions also fetches and validates the current XCFind feed before live-data changes can be merged.