from django.shortcuts import redirect
from ..decorators import login_required_ajax


@login_required_ajax
def index(request):
    """Redirect root to event list."""
    return redirect('tickets:event_list')
