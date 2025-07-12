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
]

class BlockUnauthorizedOriginsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_REFERER')
        ua = request.META.get("HTTP_USER_AGENT", "").lower()
        if "postman" in ua or "curl" in ua:
            return JsonResponse({'error': 'brother, you really gotta tri hArDeR! LOL'}, status=403)

        if origin:
            if any(origin.startswith(allowed) for allowed in ALLOWED_ORIGINS):
                return self.get_response(request)
            return JsonResponse({'error': 'ah, caught u trying something. HEHEHE 😂'}, status=403)
        email = request.session.get('email')
        person = Person.objects.filter(email = email).first()
        if person:
            return JsonResponse({'error': f"{person.name}, Bro really? if u need public API access ask PAPA SANGER! dont try to be sneeky peeky and all haa?"}, status=403)
        return JsonResponse({'error': "my brother, no public API for you, ask VISHRUT bhaiya for all this."})