from django.conf import settings

def language_context(request):
    """Add language-related context variables."""
    return {
        'redirect_to': request.get_full_path(),
        'LANGUAGES': settings.LANGUAGES,
        'LANGUAGE_CODE': request.LANGUAGE_CODE if hasattr(request, 'LANGUAGE_CODE') else settings.LANGUAGE_CODE,
    }