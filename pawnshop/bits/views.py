import os

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests

@csrf_exempt
def sign_in(request):
    if request.session.get('user_data'):
        print(request.session.get('user_data'))
    else:
        print("does not work")
    return render(request, 'bits/sign-in.html')

@csrf_exempt
def auth_receiver(request):
    token = request.POST['credential']

    try:
        user_data = id_token.verify_oauth2_token(token, requests.Request(), os.environ['GOOGLE_OAUTH_CLIENT_ID'])
    except ValueError:
        return HttpResponse(status=403)
    request.session['user_data'] = user_data
    return redirect('sign_in')

def sign_out(request):
    del request.session['user_data']
    return redirect('sign_in')

def test(request):
    return render(request, 'bits/home.html')

