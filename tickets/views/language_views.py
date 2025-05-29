"""Custom language switching view."""
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import translate_url
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST


@never_cache
@require_POST
def set_language_custom(request):
    """
    Custom language switching view that properly handles URL translation.
    Based on Django's set_language view but with better redirect handling.
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
    
    response = HttpResponseRedirect(next_url)
    
    lang_code = request.POST.get('language')
    if lang_code and lang_code in [lang[0] for lang in settings.LANGUAGES]:
        # Always translate the URL to the target language
        next_trans = translate_url(next_url, lang_code)
        if next_trans != next_url:
            response = HttpResponseRedirect(next_trans)
        
        # Set the language
        translation.activate(lang_code)
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
    
    return response