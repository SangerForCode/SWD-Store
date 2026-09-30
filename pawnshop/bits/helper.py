import os
from twilio.rest import Client
import urllib.parse
from operator import attrgetter
from django.db.models import Case, When, IntegerField, BooleanField, Value
from django.utils import timezone
from urllib.parse import urlparse
from django.conf import settings


account_sid = settings.TWILIO_ACCOUNT_SID
auth_token = settings.TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token) if account_sid and auth_token else None

def generate_whatsapp_link(phone_number, message=None):
    phone_number = get_clean_number(phone_number)
    phone_number = phone_number[1:]
    base_url = "https://wa.me/"
    if message:
      encoded_message = urllib.parse.quote(message)
      url = f"{base_url}{phone_number}?text={encoded_message}"
    else:
      url = f"{base_url}{phone_number}"
    return url

def get_clean_number(phone_number):
    phone_number = ''.join(filter(str.isdigit, phone_number))
    phone_number = phone_number.lstrip('0')
    if len(phone_number) == 10:
        phone_number = f"+91{phone_number}"
    elif len(phone_number) == 12 and phone_number.startswith("91"):
        phone_number = f"+{phone_number}"
    elif len(phone_number) == 9:
        phone_number = f"+971{phone_number}"
    elif phone_number.startswith("971"):
        phone_number = f"+{phone_number}"
    return phone_number


def verify_phone_number(phone_number):
    if client is None:
        raise RuntimeError("Twilio phone verification is not configured.")
    return client.lookups.v2.phone_numbers(phone_number).fetch().valid

def items_sort(items_list, method='0'):
    if not method:
        method = '0'
    items = list(items_list)
    method = str(method)

    unsold = [itm for itm in items if not itm.is_sold]
    sold   = [itm for itm in items if     itm.is_sold]

    if method == '0':
        key_fn, rev = attrgetter('updated_at'), True
    elif method == '1':
        key_fn, rev = attrgetter('price'), False
    elif method == '2':
        key_fn, rev = attrgetter('price'), True
    else:
        raise ValueError("Invalid method. Use '0', '1' or '2'.")

    unsold_sorted = sorted(unsold, key=key_fn, reverse=rev)
    sold_sorted   = sorted(sold,   key=key_fn, reverse=rev)

    return unsold_sorted + sold_sorted

def get_image_name(full_url):
    parsed_path = urlparse(full_url).path

    media_url = settings.MEDIA_URL
    if not media_url.startswith('/'):
        media_url = '/' + media_url
    if not media_url.endswith('/'):
        media_url += '/'

    if parsed_path.startswith(media_url):
        relative_path = parsed_path[len(media_url):]
        print(f"Relative path: {relative_path}")
        return relative_path

    return None