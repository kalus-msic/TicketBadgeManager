"""Custom language switching view."""
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import translate_url
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
import re


@never_cache
@require_POST
def set_language_custom(request):
    """
    Custom language switching view that properly handles URL translation.
    Handles the switch between prefixed (/cs/) and non-prefixed URLs.
    """
    next_url = request.POST.get('next', request.GET.get('next'))
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = request.META.get('HTTP_REFERER', '/')
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = '/'
    
    lang_code = request.POST.get('language')
    if lang_code and lang_code in [lang[0] for lang in settings.LANGUAGES]:
        # Set the language first
        translation.activate(lang_code)
        
        # Handle URL translation manually for better control
        if lang_code == 'en':
            # Remove /cs/ prefix if present
            if next_url.startswith('/cs/'):
                next_url = next_url[3:]  # Remove the first 3 characters (/cs)
                if not next_url:
                    next_url = '/'
        elif lang_code == 'cs':
            # Add /cs/ prefix if not present
            if not next_url.startswith('/cs/'):
                # Don't add prefix to admin or i18n URLs
                if not next_url.startswith(('/admin/', '/i18n/', '/static/', '/media/')):
                    # Ensure we have a leading slash
                    if not next_url.startswith('/'):
                        next_url = '/' + next_url
                    next_url = '/cs' + next_url
        
        response = HttpResponseRedirect(next_url)
        
        # Set the language cookie
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang_code,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )
    else:
        response = HttpResponseRedirect(next_url)
    
    return response