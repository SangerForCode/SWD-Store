from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware

class DomainBasedCSRFMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        allowed_domain = 'https://admin.amazoff.shop'

        origin = request.META.get('HTTP_ORIGIN')
        if origin == allowed_domain:
            return None

        return super().process_view(request, callback, callback_args, callback_kwargs)
