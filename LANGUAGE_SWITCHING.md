# Language Switching Configuration

## How it works

The application supports bilingual mode (English/Czech) with the following configuration:

- **Default language**: English (no URL prefix)
- **Czech language**: Uses `/cs/` URL prefix
- **Language cookie**: Stores user's language preference

## URL Structure

- English: `/tickets/`, `/import/`, `/settings/` etc.
- Czech: `/cs/tickets/`, `/cs/import/`, `/cs/settings/` etc.

## Configuration Details

### 1. Settings (`settings.py`)

```python
LANGUAGE_CODE = 'en'  # Default language
LANGUAGES = [
    ('en', _('English')),
    ('cs', _('Czech')),
]
USE_I18N = True
LOCALE_PATHS = [BASE_DIR / 'locale']
```

### 2. URL Configuration (`urls.py`)

```python
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching
    path('admin/', admin.site.urls),
]

urlpatterns += i18n_patterns(
    path('', include('tickets.urls')),
    prefix_default_language=False,  # No /en/ prefix for English
)
```

### 3. Middleware Order

The `LocaleMiddleware` must be after `SessionMiddleware`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Here
    'django.middleware.common.CommonMiddleware',
    # ...
]
```

## Language Switcher

The language switcher is in `templates/includes/language_switcher.html`:

```django
<form action="{% url 'set_language' %}" method="post">
    {% csrf_token %}
    <input name="next" type="hidden" value="{{ request.get_full_path }}" />
    <select name="language" onchange="this.form.submit()">
        <!-- Options for each language -->
    </select>
</form>
```

## Troubleshooting

### Problem: Can't switch back from Czech to English

**Cause**: The language switcher might not properly handle the URL translation between `/cs/path/` and `/path/`.

**Solutions**:

1. **Clear browser cookies** - This resets the language preference
2. **Manually remove `/cs/` from URL** - Quick workaround
3. **Check middleware order** - Ensure `LocaleMiddleware` is correctly positioned

### Problem: 404 errors after language switch

**Cause**: URL patterns might not be properly configured for i18n.

**Solution**: Ensure all URL patterns are wrapped in `i18n_patterns()`.

## Best Practices

1. Always use `{% load i18n %}` in templates that need translation
2. Use `{% trans "text" %}` for all user-facing strings
3. Run `compilemessages` after updating .po files
4. Test language switching on all major pages

## Manual Language Switch

You can manually switch languages by:

1. **URL**: Add or remove `/cs/` prefix
2. **Cookie**: Set `django_language` cookie to `en` or `cs`
3. **Session**: The language preference is stored in the session

## API Endpoints

- `/i18n/setlang/` - POST endpoint for language switching
- Accepts: `language` (en/cs) and `next` (redirect URL)

## Debug Tips

To debug language issues:

1. Check current language: `{% get_current_language as LANGUAGE_CODE %}`
2. Check available languages: `{% get_available_languages as LANGUAGES %}`
3. Check browser's Accept-Language header
4. Verify cookie value in browser developer tools