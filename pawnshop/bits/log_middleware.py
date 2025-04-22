import logging
from datetime import datetime
from bits.models import *

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("request_logger")

    def __call__(self, request):
        email = None
        person = -1
        if request.session.get('user_data'):
            email = request.session.get('user_data')['email']
            if Person.objects.filter(email=email).exists():
                person = Person.objects.get(email=email).id
        ip = self.get_client_ip(request)
        method = request.method
        path = request.get_full_path()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.logger.info(f"{timestamp} | {person} | {ip} | {method} {path}")
        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
