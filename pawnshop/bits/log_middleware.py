import logging
import requests
from datetime import datetime
from bits.models import Person
from user_agents import parse
from math import radians, sin, cos, sqrt, atan2

BITS_CAMPUSES = {
    'GOA': (15.3911442733276, 73.87815086678745),
    'HYD': (17.544822002003123, 78.57271655444397),
    'PIL': (28.359229729445914, 75.58816379595879),
    'DUB': (25.131566983306616, 55.4200293516723),
}

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("bits")

    def __call__(self, request):
        email = None
        person = None
        person_info = "-1 None"

        email = request.session.get('email')
        if email:
            person_info = email
        person = Person.objects.filter(email=email).first()
        if person:
            person_info = f"{person.id}, {person.name}"

        ip = self.get_client_ip(request)
        path = request.get_full_path()
        method = request.method
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(ua_string)
        browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
        os = f"{user_agent.os.family} {user_agent.os.version_string}"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        lat, lon = self.get_location(ip)
        lat_str = f"{lat}" if lat is not None else "None"
        lon_str = f"{lon}" if lon is not None else "None"

        campus = self.get_nearest_campus(lat, lon)

        log_message = (
            f"{timestamp} | {method} | {person_info} | {path} | {ip} | {os} | {browser} | "
            f"{lat_str} | {lon_str} | {campus} | {person.campus if person else campus}"
        )

        if person is not None and person.campus == "OTH":
            person.campus = campus
            person.save()

        self.logger.info(log_message)

        return self.get_response(request)

    def get_client_ip(self, request):
        return request.META.get('HTTP_CF_CONNECTING_IP') or (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        ) or request.META.get('REMOTE_ADDR')

    def get_location(self, ip):
        try:
            res = requests.get(f"https://web-api.nordvpn.com/v1/ips/lookup/{ip}", timeout=10)
            data = res.json()
            return data.get('latitude'), data.get('longitude')
        except Exception as e:
            logging.warning(f"Could not get location for IP {ip}: {e}")
            return None, None

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def get_nearest_campus(self, lat, lon):
        if lat is None or lon is None:
            return "OTH"

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return "OTH"

        min_dist = float('inf')
        nearest = "OTH"
        for campus, (clat, clon) in BITS_CAMPUSES.items():
            dist = self.haversine(lat, lon, clat, clon)
            if dist < min_dist:
                min_dist = dist
                nearest = campus
        return nearest
