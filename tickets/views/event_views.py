from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.db.models import Count

from ..models import Event, Ticket, CheckIn
from ..decorators import staff_required


@staff_required
def event_list(request):
    """Event list dashboard."""
    show_archived = request.GET.get('archived') == '1'
    if show_archived:
        events = Event.objects.all()
    else:
        events = Event.objects.filter(status='active')
    events = events.annotate(
        ticket_count=Count('tickets'),
        checkin_count=Count('tickets__checkin'),
    )
    return render(request, 'tickets/event_list.html', {
        'events': events, 'show_archived': show_archived,
    })


@staff_required
def event_create(request):
    """Create a new event."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        date_str = request.POST.get('date', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', 'active')
        if not name or not date_str:
            messages.error(request, _("Name and date are required."))
            return render(request, 'tickets/event_form.html', {'form_data': request.POST, 'event': None})
        from datetime import datetime
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, _("Invalid date format. Use YYYY-MM-DD."))
            return render(request, 'tickets/event_form.html', {'form_data': request.POST, 'event': None})
        event = Event.objects.create(
            name=name, date=event_date, description=description, status=status,
        )
        messages.success(request, _("Event created successfully."))
        return redirect('tickets:ticket_list', event_pk=event.pk)
    return render(request, 'tickets/event_form.html', {'event': None})


@staff_required
def event_edit(request, event_pk):
    """Edit an existing event."""
    event = get_object_or_404(Event, pk=event_pk)
    if request.method == 'POST':
        event.name = request.POST.get('name', event.name).strip() or event.name
        date_str = request.POST.get('date', '').strip()
        if date_str:
            from datetime import datetime
            try:
                event.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, _("Invalid date format."))
                return render(request, 'tickets/event_form.html', {'event': event})
        event.description = request.POST.get('description', event.description)
        event.status = request.POST.get('status', event.status)
        event.printer_1_name = request.POST.get('printer_1_name', event.printer_1_name).strip() or event.printer_1_name
        event.printer_2_name = request.POST.get('printer_2_name', event.printer_2_name).strip() or event.printer_2_name
        event.save()
        messages.success(request, _("Event updated."))
        return redirect('tickets:event_list')
    return render(request, 'tickets/event_form.html', {'event': event})


@staff_required
def event_delete(request, event_pk):
    """Delete an event."""
    event = get_object_or_404(Event, pk=event_pk)
    if request.method == 'POST':
        event.delete()
        messages.success(request, _("Event deleted."))
        return redirect('tickets:event_list')
    return render(request, 'tickets/event_confirm_delete.html', {'event': event})
