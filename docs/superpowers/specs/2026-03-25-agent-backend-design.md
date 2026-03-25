# Agent Backend + WebUSB UI Fixes — Design Spec (Phase 3)

## Problem

Two separate issues addressed in this spec:

1. **WebUSB UI bugs** — Settings page doesn't show which USB printer is paired per queue (DOMContentLoaded timing bug). Scanner/kiosk gear panel shows control buttons but not the name of the currently paired printer.

2. **Agent backend missing** — Mobile devices cannot use WebUSB (no USB-A port). Users want to scan from a phone and print to a USB printer connected to a nearby PC. The current codebase has `direct` and `webusb` backends but no `agent` backend.

## Deployment Context

- **Self-hosted**: User runs Django on their own PC/server. `direct` backend works fine (same machine). Agent is optional.
- **odbavto.cz SaaS**: Django runs in the cloud. Agent runs on the PC with the USB printer. Mobile browser scans → cloud server queues job → agent polls → prints.

Because the Django server may be remote (cloud), the agent **initiates the connection** to the server (polling). The server never connects to the agent directly.

## Part 1: WebUSB UI Bug Fixes

### Bug 1 — Settings: paired device name shows `—`

**Root cause:** The inline `<script>` in `settings.html` registers a `DOMContentLoaded` listener after the event has already fired (script is at the bottom of the DOM). The listener never executes, so localStorage is never read and the status spans stay at their default `—`.

**Fix:** Remove the `addEventListener('DOMContentLoaded', ...)` wrapper and execute the localStorage read immediately — at that point in script execution the DOM is already fully parsed.

**File:** `tickets/templates/tickets/settings.html`

### Bug 2 — Scanner/Kiosk: gear panel shows no printer name

**Root cause:** The gear panel (`#webusb-gear-panel`) contains only action buttons (Změnit tiskárnu, Odpárovat) with no label displaying the currently paired printer name.

**Fix:** Add `<span id="webusb-gear-printer-name" class="me-2 fw-semibold"></span>` inside the gear panel. `print-manager.js` populates it every time `setStatus()` is called (on `initStatusCheck`, after pairing, after each print). When state is `unpaired`, show "Nepárováno".

**Files:** `tickets/templates/tickets/scanner.html`, `tickets/templates/tickets/kiosk.html`, `tickets/static/js/print-manager.js`

## Part 2: Agent Backend

### Topology

```
Mobile browser (odbavto.cz)          PC at entrance
├── Scanner page                     ├── agent.py / agent.exe
│   └── POST /events/<pk>/verify/    │   ├── polls /agent/poll/ every 2s
│       ← {status: 'ok'}            │   ├── prints via TSCLIB (Win) / lpr (Linux/macOS)
│       (no print data sent         │   └── POST /agent/ack/ when done
│        to mobile browser)         └── USB Printer
```

The mobile browser receives only `{status: 'ok'}` — no print data is sent to the client.

### Django changes

#### Event model — new field

```python
agent_token = models.CharField(max_length=64, blank=True,
                               verbose_name=_("Agent Token"))
```

Generated as UUID4 in settings view on first save or on explicit "Regenerate" action. Displayed in Settings UI when `print_backend == 'agent'`.

#### New model: PrintJob

```python
class PrintJob(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('printing', 'Printing'),
        ('done',     'Done'),
        ('error',    'Error'),
    ]
    event         = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='print_jobs')
    ticket        = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True)
    printer_queue = models.IntegerField(default=1)
    print_data    = models.TextField()          # base64-encoded TSC bytes
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    completed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
```

#### New view file: `tickets/views/agent_views.py`

Two endpoints:

**Poll endpoint**
- `GET /events/<pk>/agent/poll/`
- Query param: `?queue=1` (required)
- Auth: `X-Agent-Token` header matched against `event.agent_token`
- Returns oldest `pending` PrintJob for the given event + queue, or `{}` if none
- On job found: sets status → `printing`
- No `@staff_required` — uses token auth only. Decorated with `@csrf_exempt`.

**Ack endpoint**
- `POST /events/<pk>/agent/ack/`
- Body: `{job_id, success: true/false, error: "..."}`
- Auth: same `X-Agent-Token`
- Sets status → `done` (success) or `error` + stores `error_message` + sets `completed_at`

#### AgentBackend in `printing_service.py`

```python
class AgentBackend:
    def print(self, ticket, event, image_bytes, printer_queue):
        PrintJob.objects.create(
            event=event,
            ticket=ticket,
            printer_queue=printer_queue,
            print_data=base64.b64encode(image_bytes).decode(),
            status='pending',
        )
        return {'status': 'ok'}
```

`PrintManager.print_ticket()` calls `AgentBackend.print()` when `event.print_backend == 'agent'`. The result `{status: 'ok'}` is passed through to the browser — identical shape to a successful check-in without printing.

#### Settings UI — agent section

Shown (via JS show/hide, same pattern as WebUSB section) when `print_backend == 'agent'`:

- Agent Token field: read-only input + Copy button + Regenerate button
- Server URL display (for paste into `agent_config.ini`)
- Brief instructions: download `agent.py`, copy `agent_config.ini.example`, fill in token + event_pk, run `python agent.py`

### agent.py

**Location:** project root (`agent.py` + `agent_config.ini.example`)

**Configuration (`agent_config.ini`):**
```ini
[server]
url = https://odbavto.cz
event_pk = 3
token = paste-agent-token-here
poll_interval = 2

[printers]
queue_1 = TDP-2251
queue_2 =
```

**Dependencies:** stdlib only (`http.client`, `configparser`, `time`, `base64`, `ctypes`). PyInstaller-compatible with no changes.

**Print backends in agent.py:**

| Platform | Method |
|----------|--------|
| Windows  | TSCLIB.dll via ctypes — same logic as Django `DirectBackend` |
| Linux    | `lpr -P <name>` subprocess call |
| macOS    | `lpr -P <name>` subprocess call |

Platform detected at startup via `sys.platform`. If TSCLIB not found on Windows, agent logs error and marks job as `error`.

**Main loop:**
```
configure from agent_config.ini (or CLI args --url --event --token)
detect platform + verify printer reachable (warn if not, don't exit)

while True:
    for queue in configured_queues:
        job = GET /events/<pk>/agent/poll/?queue=<q>  (X-Agent-Token header)
        if job:
            success, error = print_bytes(base64.decode(job.print_data), queue)
            POST /events/<pk>/agent/ack/ {job_id, success, error}
    sleep(poll_interval)
```

**Concurrency:** Sequential within one agent instance (FIFO per queue). Multiple simultaneous scans queue up in DB — each poll cycle drains one job per queue. Acceptable for entrance use case.

**Distribution:**
- Now: `agent.py` + `agent_config.ini.example` in repo root, documented in README
- Future: `pyinstaller --onefile agent.py` → `agent.exe` (no code changes needed)

## Files Modified / Created

```
MODIFY: tickets/models.py
  — add agent_token to Event
  — add PrintJob model

CREATE: tickets/migrations/00XX_printjob_agent_token.py

CREATE: tickets/views/agent_views.py
  — poll_endpoint(), ack_endpoint()

MODIFY: tickets/views/__init__.py
  — export new views

MODIFY: tickets/urls.py
  — add /agent/poll/ and /agent/ack/ routes

MODIFY: tickets/services/printing_service.py
  — add AgentBackend class
  — PrintManager.print_ticket() handles 'agent' backend

MODIFY: tickets/views/settings_views.py
  — handle agent_token generation / regeneration

MODIFY: tickets/templates/tickets/settings.html
  — fix DOMContentLoaded bug (Bug 1)
  — add agent settings section (token display, instructions)

MODIFY: tickets/templates/tickets/scanner.html
  — add printer name span to gear panel (Bug 2)

MODIFY: tickets/templates/tickets/kiosk.html
  — add printer name span to gear panel (Bug 2)

MODIFY: tickets/static/js/print-manager.js
  — populate #webusb-gear-printer-name in setStatus()

CREATE: agent.py
CREATE: agent_config.ini.example

MODIFY: docs/ROADMAP.md
  — Phase 3 updated (polling approach, WebSocket upgrade path noted)
  — Add multi-tenancy section (future, no code)
  — Add rename note
```

## Constraints

- `agent.py` must use stdlib only — no pip installs, no `requirements.txt` changes.
- Poll endpoint is `@csrf_exempt` + token auth (no Django session needed).
- `print_data` stored as base64 text in DB — acceptable for label-sized payloads (~5–20 KB per job).
- `PrintJob` records are never auto-deleted — cleanup policy TBD (future roadmap item).
- Agent WebSocket upgrade: `poll` endpoint stays. New WebSocket consumer added alongside. Agent config gains `transport = polling|websocket`. PrintJob model unchanged.

## Out of Scope

- WebSocket / Django Channels (future upgrade — see Roadmap)
- PyInstaller .exe build (documented, not automated)
- Multi-tenancy (Roadmap note only)
- Linux kernel USB raw write (`/dev/usb/lp0`) — use `lpr` only for now; raw path added later
- PrintJob admin/log view in Django UI (future)
- Agent auto-update mechanism
