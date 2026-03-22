from django.conf import settings

from .models import Event


def language_context(request):
    """Add language-related context variables."""
    return {
        'redirect_to': request.get_full_path(),
        'LANGUAGES': settings.LANGUAGES,
        'LANGUAGE_CODE': request.LANGUAGE_CODE if hasattr(request, 'LANGUAGE_CODE') else settings.LANGUAGE_CODE,
    }


def events_context(request):
    """Inject active event and events list into all templates."""
    active_event = None
    events_list = []
    if hasattr(request, 'resolver_match') and request.resolver_match:
        pk = request.resolver_match.kwargs.get('event_pk')
        if pk:
            active_event = Event.objects.filter(pk=pk).first()
    events_list = list(Event.objects.filter(status='active').order_by('-date'))
    return {'active_event': active_event, 'events_list': events_list}