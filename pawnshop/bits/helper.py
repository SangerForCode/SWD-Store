import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import urllib.parse

load_dotenv()

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
client = Client(account_sid, auth_token)

service = client.verify.v2.services.create(
    friendly_name="Bits Pilani Pawnshop"
)


def generate_whatsapp_link(phone_number, message=None):
    base_url = "https://wa.me/"
    if message:
      encoded_message = urllib.parse.quote(message)
      url = f"{base_url}{phone_number}?text={encoded_message}"
    else:
      url = f"{base_url}{phone_number}"
    return url

def verify_phone_number(phone_number):
    return client.lookups.v2.phone_numbers(phone_number).fetch().valid