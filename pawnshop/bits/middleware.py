from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware
from bits.models import Person
from django.http import JsonResponse

from django.middleware.csrf import CsrfViewMiddleware

class DomainBasedCSRFMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        allowed_domains = ['https://admin.bits-pilani.store']

        origin = request.META.get('HTTP_ORIGIN', '')
        referer = request.META.get('HTTP_REFERER', '')

        if origin in allowed_domains or any(referer.startswith(d) for d in allowed_domains):
            request.csrf_processing_done = True
            return None

        return super().process_view(request, callback, callback_args, callback_kwargs)

ALLOWED_ORIGINS = [
    'https://bits-pilani.store',
    'https://www.bits-pilani.store',
    'https://admin.bits-pilani.store',
]

class BlockUnauthorizedOriginsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        if any(x in ua for x in ('postman', 'curl')):
            return JsonResponse({'error': 'sneaky sneaky, denied'}, status=403)

        host = request.get_host()
        if host in ALLOWED_ORIGINS:
            return self.get_response(request)

        origin = request.META.get('HTTP_ORIGIN')
        if origin and any(origin.startswith(a) for a in ALLOWED_ORIGINS):
            return self.get_response(request)

        email = request.session.get('email')
        if email:
            person = Person.objects.filter(email=email).first()
            if person:
                return JsonResponse(
                    {'error': f"{person.name}, Bro really? dont try to be sneeky peeky?"},
                    status=403
                )

        return JsonResponse({'error': "my brother, no public API for you."}, status=403)
