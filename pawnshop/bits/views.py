from django.shortcuts import render
from django.contrib.auth import logout

def home(request):
    return render(request, "bits/home.html")

def logout_view(request):
    logout(request)
    return render(request, "bits/home.html")