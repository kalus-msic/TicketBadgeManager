# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0-stable] - 2026-09-28

Upgrade: run `update_app.bat` (or `python manage.py migrate` + `collectstatic`).
Migrations 0016-0023. URLs are now event-scoped; existing tickets move into a default event.

### Added
- **Events System**: multi-event support with `/events/<id>/` URL scoping, event CRUD, per-event settings, navbar event switcher.
- **Print backends**: printer-agnostic `PrintManager` with three backends - Direct (TSCLIB.dll), WebUSB (browser to USB printer, pairing UI + Zadig guide) and print Agent (`agent.py` polling, token auth, atomic job claiming).
- **Label copies**: configurable number of label copies per check-in.
- **Eventee sync**: one-click bulk sync of all tickets (ticket number pushed, scannable at the door); reverse check against Eventee (only in Eventee / missing in Eventee / cancelled but present) with import and re-push actions; imported attendees get our QR code written back to Eventee.
- **Eventee invitation e-mails**: per-event toggle; the invite e-mail is sent only once (or when the e-mail changes), data edits sync silently. Per-event default for the "Sync to Eventee" checkbox on new tickets.
- **CLI**: `python manage.py sync_eventee <event_id> [--reconcile]`.
- **Import without QR column**: automatic `GUEST-XXXXXXXX` codes (e-mail dedup in append/update); manual ticket creation uses the same format.
- **GoOut merge**: two-file import (check-in + transactions) with CSV/XLSX support.
- **XLSX export** alongside CSV.
- **MSIC design system**: brand colours (#004990, #EE2E27, #00ADD0), reorganised navbar, stat cards, new screenshots.
- **Static files** served by WhiteNoise when `DEBUG=False`.

### Changed
- **URL structure**: all ticket pages are scoped under an event.
- **Eventee payload**: snake_case `first_name`/`last_name`, API host `api.eventee.com`, per-event token only (no `.env` token).
- **update_app.bat**: main/dev aware, runs collectstatic and compiles translations; SSL via `runserver_plus`.
- **Security**: Django 5.1.9 -> 5.2.12, requests 2.32.3 -> 2.32.5.

### Fixed
- Eventee did not receive attendee names (camelCase payload).
- Editing a ticket crashed with "An unexpected error occurred" (change tracking).
- CSV/XLSX export timestamps now in local time (Europe/Prague).
- CSV delimiter detection, translations, `.env` generation and installation scripts.

## [1.1.1-stable] - 2025-06-17

### Added
- Improved smart import for Ti.to with better mapping.

## [1.1-stable] - 2025-06-12

### Fixed
- Issues with creating `.env` files during installation.

## [1.0-stable] - 2025-05-05

### Added
- Initial stable release.
- "Verify & Print" action in ticket list.
- Improved scanner navigation.

---
