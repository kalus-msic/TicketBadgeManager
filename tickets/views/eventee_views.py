from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from ..decorators import staff_required
from ..models import Event, Log
from ..services.eventee_service import EventeeService
from ..utils.auth_utils import get_username_for_log


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
