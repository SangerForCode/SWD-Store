from django.conf import settings


def vapid_public_key(request):
    """Expose the configured public Web Push key to templates."""
    return {"VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY}
