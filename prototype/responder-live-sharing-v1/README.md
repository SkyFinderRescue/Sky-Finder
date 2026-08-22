# Responder Live Sharing Prototype v1

**Status: isolated prototype — NOT connected to production SkyFinder and NOT field-ready.**

This prototype exists to prove a small, secure, real-time responder-location layer before any integration with the working SkyFinder application.

## Production safety rule

- Development branch: `prototype/responder-live-sharing-v1`
- Production `main` is not modified by this prototype.
- All prototype files live under `prototype/responder-live-sharing-v1/`.
- The prototype validation workflow fails if this branch changes files outside the prototype directory or its own branch-only workflow.
- Do not merge this branch into `main` until the responder system has passed multi-phone testing and a separate SkyFinder integration review.

## Design goals

1. A responder opens the app, authenticates, grants location permission, and becomes visible to the other authenticated users in the common operational group.
2. No QR code or same-time arrival is required.
3. Approximately 10–12 simultaneous users.
4. Each responder has a callsign and a live marker.
5. Every marker carries freshness state: LIVE, DELAYED, or STALE. Old positions never masquerade as live positions.
6. A short rolling breadcrumb track is stored for each responder.
7. Loss of connectivity changes presence state instead of silently removing the responder.
8. Location data is temporary and separated from SkyFinder pilot/XCFind data.
9. Internal fields are intentionally compatible with a future Cursor-on-Target mapping without depending on TAK/WFTAK.

## Backend

Target backend: Firebase Realtime Database + Firebase Authentication on the free Spark plan for prototype use.

The app is backend-adapter based. `firebase-backend.mjs` can later be replaced without rewriting the map/UI.

## Prototype modes

- **Mock mode:** works without Firebase and simulates additional responders so UI/freshness logic can be tested safely.
- **Firebase mode:** enabled only after a separate Firebase project is created and a `firebase-config.js` file is supplied locally/deployed to the prototype branch. The config object is not a secret, but the database Security Rules are the actual access-control boundary.

## Security posture for v1

The supplied Firebase rules:

- deny unauthenticated reads and writes;
- let authenticated users read the common test room;
- let a user write only their own responder record and own breadcrumb slots;
- validate latitude/longitude and basic field types;
- reject unrecognized responder fields.

For the first proof of concept, anonymous Firebase Authentication is used to get two-phone testing running with minimal setup. **Anonymous auth is not sufficient for a production/public deployment.** Before any field use, replace it with allowlisted accounts or stronger identity controls.

## Freshness behavior

With a nominal moving update interval of 5 seconds:

- LIVE: last server update <= 15 seconds and currently connected
- DELAYED: last server update <= 60 seconds
- STALE: > 60 seconds or clearly disconnected beyond the delay window

The UI always displays the age of the last update.

## Breadcrumb storage

Each responder writes into a 120-slot ring buffer. At a 15-second breadcrumb cadence this represents about 30 minutes without unbounded database growth.

## Next external dependency

A Firebase project must be created before true phone-to-phone real-time testing. No Firebase connector is currently available in this ChatGPT environment, so the repository foundation is being prepared first without touching production SkyFinder.
