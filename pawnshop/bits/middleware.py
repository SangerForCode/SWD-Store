from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware
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

ALLOWED_ORIGINS = 'https://bits-pilani.store'

class BlockUnauthorizedOriginsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_REFERER')
        if origin:
            if origin.startswith(ALLOWED_ORIGINS):
                return self.get_response(request)
            return JsonResponse({'error': 'Bro dont try to play the fool with me'}, status=403)
        return JsonResponse({'error': 'try your best not to play the fool with me'}, status=403)
