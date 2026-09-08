from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..decorators import staff_required
from ..models import Event, Log, Ticket
from ..services.eventee_service import EventeeService
from ..utils.auth_utils import get_username_for_log
from ..utils.guest_codes import generate_guest_code, existing_qr_codes


@staff_required
def sync_eventee(request, event_pk):
    """Send all needs_sync tickets of the event to Eventee."""
    event = get_object_or_404(Event, pk=event_pk)
    if request.method != "POST":
        return redirect("tickets:settings", event_pk=event_pk)
    result = EventeeService(event=event).sync_event(event)
    Log.objects.create(
        event=event, event_type="SYSTEM",
        message=(f"Eventee sync by {get_username_for_log(request)}: "
                 f"total={result['total']} done={result['done']} failed={result['failed']}"),
    )
    messages.success(
        request,
        f"Eventee sync: done {result['done']}/{result['total']}, failed {result['failed']}",
    )
    return redirect("tickets:settings", event_pk=event_pk)


@staff_required
def reconcile_eventee(request, event_pk):
    """Show a report of differences against Eventee."""
    event = get_object_or_404(Event, pk=event_pk)
    result = EventeeService(event=event).reconcile(event)
    return render(request, "tickets/reconcile.html", {"event": event, "result": result})


@staff_required
def reconcile_apply(request, event_pk):
    """Import selected Eventee-only people and re-push selected missing ones."""
    event = get_object_or_404(Event, pk=event_pk)
    if request.method != "POST":
        return redirect("tickets:reconcile_eventee", event_pk=event_pk)

    import_emails = request.POST.getlist("import_email")
    repush_qrs = request.POST.getlist("repush_qr")

    # 1) Import Eventee-only people as local tickets (prefix EV, already synced).
    imported = 0
    if import_emails:
        used = existing_qr_codes()
        for email in import_emails:
            email = email.strip()
            if not email:
                continue
            exists = Ticket.objects.filter(event=event, email__iexact=email).exists()
            if exists:
                continue
            Ticket.objects.create(
                event=event,
                qr_code=generate_guest_code(used, prefix="EV"),
                name=request.POST.get(f"name_{email}", "") or email,
                email=email,
                status="VALID",
                eventee_email=email,
                needs_sync=False,
                synced_at=timezone.now(),
                invited=True,
            )
            imported += 1

    # 2) Re-push missing ones - mark needs_sync and run sync.
    repushed = 0
    if repush_qrs:
        Ticket.objects.filter(event=event, qr_code__in=repush_qrs).update(needs_sync=True)
        EventeeService(event=event).sync_event(event)
        repushed = len(repush_qrs)

    messages.success(request, f"Reconcile: imported {imported}, re-push {repushed}")
    return redirect("tickets:reconcile_eventee", event_pk=event_pk)
