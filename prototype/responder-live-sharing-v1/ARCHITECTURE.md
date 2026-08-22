# Architecture Notes — Responder Live Sharing v1

## Separation from SkyFinder

This prototype is intentionally not imported, referenced, or deployed by the production SkyFinder page. It lives on a dedicated Git branch and under a dedicated directory.

Production SkyFinder continues to own:
- XCFind pilot data
- paraglider status/markers
- rescue target selection
- navigation/W3W
- production map UI

Responder Live Sharing owns only temporary responder identity, presence, GPS points, and rolling breadcrumbs.

## User flow

The long-term flow is deliberately generic rather than QR-code based:

1. User opens the responder-capable application.
2. User authenticates with their individual account.
3. If location permission was previously granted, the location watcher can start immediately; otherwise the browser/OS prompts once.
4. The responder appears in the common authorized operational group.
5. Users arriving later join the same group automatically.
6. Each client continuously receives the newest responder positions.
7. A disconnect or missing update causes the marker to age through LIVE -> DELAYED -> STALE.
8. The user can explicitly Stop Sharing.

For the first proof of concept, the room is `general`. A later account record can assign users to groups without requiring QR codes or same-time arrival.

## Data model

`rooms/general/responders/{uid}`

- `callsign`
- `lat`, `lng`
- `hae_m` — height above ellipsoid when available
- `ce_m` — circular/horizontal GPS error estimate
- `le_m` — vertical error estimate when available
- `heading_deg`
- `speed_mps`
- `device_time_ms`
- `server_time_ms`
- `online`
- `freshness_ttl_ms`
- `session_id`

These field concepts intentionally map cleanly to future Cursor-on-Target semantics such as time, stale, point, CE, and LE without requiring TAK infrastructure.

`rooms/general/tracks/{uid}/{slot}` is a fixed 120-slot ring buffer, preventing unlimited history growth.

## Freshness is server-oriented

Client clocks can be wrong. Display freshness should therefore prefer Firebase `server_time_ms` rather than trusting only the phone timestamp. `device_time_ms` is retained for diagnostics and future sequencing.

## Failure behavior

A critical design requirement is that communication failure never looks like a live position.

- Firebase `onDisconnect` marks the user offline and records a server-side last-seen time.
- The map never hides age information.
- A disconnected responder remains visible as a last-known point and ages to DELAYED/STALE.
- Future integration should retain this behavior even if the backend changes.

## Location update policy

Starting prototype policy:
- moving: publish latest position about every 5 seconds;
- stationary: back off to about every 20 seconds;
- breadcrumb: about every 15 seconds when meaningful movement occurred;
- no unbounded history.

This is intentionally conservative for battery, cellular usage, and free-tier backend usage.

## Privacy/security gates before field use

The first Firebase connection uses anonymous auth only for controlled two-phone proof-of-concept testing. Before any real-world deployment:

1. Replace anonymous auth with allowlisted user accounts or equivalent stronger auth.
2. Add server-enforced group membership.
3. Limit who can read responder locations.
4. Add automatic session/location retention cleanup.
5. Add an audit-safe but privacy-minimal administrative model.
6. Test compromised/unauthorized client behavior.
7. Test actual iPhone and Android devices, poor service, reconnection, screen lock/backgrounding, GPS drift, and battery impact.

## iPhone limitation to prove

The backend can be realtime, but browser GPS background behavior is controlled by iOS. The prototype must measure what happens when Safari/PWA is backgrounded or the screen locks. If location updates become unreliable, the correct next step is a small native tracking component rather than pretending the web app is continuously live.
