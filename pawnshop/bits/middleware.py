from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware

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
