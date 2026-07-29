# Sky Finder

California paraglider rescue locator built for fast field use.

## Production workflow

- Live pilot tracking is displayed from the XCFind California group (`id=16`).
- Sky Finder obtains the responder's device GPS location.
- Paste the pilot's latest verified XCFind coordinates to get:
  - straight-line distance in miles
  - bearing
  - Apple Maps directions
  - Google Maps directions
  - what3words map handoff
  - copy/share tools
- If the embedded XCFind view is restricted by a browser, **Open Full XCFind** provides a direct fallback.

## Safety design

Sky Finder does not guess the newest pilot position from track-point numbering and does not use an unverified scraper. Verify the pilot identity, timestamp, and coordinates in XCFind before committing resources.

## Deployment

The production app is static and designed for GitHub Pages. GPS requires a secure context (HTTPS).

## Validation

Run:

```bash
python scripts/validate.py
```

GitHub Actions runs the same production validation on pushes and pull requests.
