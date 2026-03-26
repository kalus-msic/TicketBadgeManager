import hmac
import json
import uuid
from datetime import timedelta
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..models import Event, PrintJob
from ..decorators import staff_required

STALE_PRINTING_TIMEOUT_SECONDS = 60


def _verify_token(request, event):
    """Verify X-Agent-Token header against event.agent_token using constant-time comparison.
    Returns False if event.agent_token is empty (prevents accepting unauthenticated requests).
    """
    if not event.agent_token:
        return False
    incoming = request.META.get('HTTP_X_AGENT_TOKEN', '')
    return hmac.compare_digest(incoming, event.agent_token)


@csrf_exempt
@require_http_methods(['GET'])
def agent_poll(request, event_pk):
    """Poll for the next pending print job. Called every ~2s by agent.py."""
    event = get_object_or_404(Event, pk=event_pk)
    if not _verify_token(request, event):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    queue = request.GET.get('queue', '1')[:2]
    stale_cutoff = timezone.now() - timedelta(seconds=STALE_PRINTING_TIMEOUT_SECONDS)
    with transaction.atomic():
        # Recover stale jobs stuck in 'printing' state (e.g. agent crashed)
        PrintJob.objects.filter(
            event=event, printer_queue=queue, status='printing', created_at__lt=stale_cutoff
        ).update(status='pending')
        # Atomically claim the next pending job to prevent double-printing
        job = PrintJob.objects.select_for_update().filter(
            event=event, printer_queue=queue, status='pending'
        ).first()
        if not job:
            return JsonResponse({})
        job.status = 'printing'
        job.save(update_fields=['status'])
    return JsonResponse({
        'job_id': job.pk,
        'print_data': job.print_data,
        'printer_queue': job.printer_queue,
    })


@csrf_exempt
@require_http_methods(['POST'])
def agent_ack(request, event_pk):
    """Acknowledge completion (or failure) of a print job."""
    event = get_object_or_404(Event, pk=event_pk)
    if not _verify_token(request, event):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    job = get_object_or_404(PrintJob, pk=data.get('job_id'), event=event)
    if job.status not in ('printing', 'pending'):
        return JsonResponse({'error': 'Job already completed'}, status=409)
    job.status = 'done' if data.get('success') else 'error'
    job.error_message = str(data.get('error', ''))[:500]
    job.completed_at = timezone.now()
    job.save(update_fields=['status', 'error_message', 'completed_at'])
    return JsonResponse({'ok': True})


@staff_required
@require_http_methods(['POST'])
def regenerate_agent_token(request, event_pk):
    """Generate a new agent token for the event. Staff-only."""
    event = get_object_or_404(Event, pk=event_pk)
    event.agent_token = uuid.uuid4().hex
    event.save(update_fields=['agent_token'])
    return JsonResponse({'token': event.agent_token})
