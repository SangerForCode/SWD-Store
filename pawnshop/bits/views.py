banned_list = []
NOTIFICATION_COOLDOWN = 10 #minutes nigga

import os
import json
import logging
import threading
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import EmailMessage
from queue import Queue
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from collections import Counter
from google.oauth2 import id_token
from google.auth.transport import requests
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import *
from pywebpush import webpush, WebPushException
from .forms import *
from django.utils import timezone
from django import forms
from django.conf import settings
import requests as req
from . import helper
from datetime import datetime, timedelta
from user_agents import parse
from django.db.models import Q
import random
from django.http import HttpResponse
from django.core.signing import Signer, BadSignature

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.messaging_response import MessagingResponse
import re
from bp_bot.bot import save_bp_reading

@csrf_exempt
def bp_bot_webhook(request):
    if request.method == 'POST':
        msg = request.POST.get('Body', '').strip().lower()

        response = MessagingResponse()

        if re.match(r'^\d+/\d+$', msg):
            saved = save_bp_reading(msg)
            if saved:
                response.message(f"Over Mummy!!! I saved {msg} 🥰💖 I love you mummy!!!")
            else:
                response.message("ayyo mummy!! something is wrong, call me and tell me what happened 😢")
        elif 'get report' in msg:
            response.message("Mummy's Report ready: https://bits-pilani.store/media/bp_bot/bp_log.xlsx")
        else:
            response.message("what what things, at what what time, happenooo happen!! MUMMY THIS IS ONLY FOR BP! if you want to talk to me then message me directly!! I love youuuuu 💖💖")

        return HttpResponse(str(response), content_type='text/xml')
    return HttpResponse("OK")


#EMAIL SHIT STARTS HERE
signer = Signer()

def generate_unsubscribe_token(user):
    return signer.sign(user.email)

def get_email_from_token(token):
    try:
        return signer.unsign(token)
    except BadSignature:
        return None

def unsubscribe_view(request, token):
    email = get_email_from_token(token)
    if not email:
        return HttpResponse("Invalid unsubscribe link.", status=400)
    user = get_object_or_404(Person, email=email)
    if not user:
        return HttpResponse("User does not exist.", status=404)
    user.is_subscribed = False
    user.save()
    return HttpResponse("You have been unsubscribed successfully.")

##EMAIL SHIT ENDS HERE

VAPID_PRIVATE_KEY = "***REMOVED***"
VAPID_CLAIMS = {
    "sub": "mailto:contact@example.com"
}

# upgraded_analytics/views.py
LOGFILE = os.path.join(settings.LOG_DIR, 'request_logs.log')

METRICS = {
    'requests': {
        'label': 'Number of Requests',
        'extractor': lambda e: True,
    },
    'unique_visitors': {
        'label': 'Unique Visitors',
        'extractor': lambda e: e['ip'],
    },
    'registered_requests': {
        'label': 'Registered Requests',
        'extractor': lambda e: e['person'] != "-1 None",
    },
    'unique_registered_visitors': {
        'label': 'Unique Registered Visitors',
        'extractor': lambda e: e['ip'] if e['person'] != "-1 None" else False,
    },
    'items_added': {
        'label': 'Items Added',
        'extractor': lambda e: e['method'] == 'POST' and e['path'].startswith('/add-product'),
    },
    'items_updated': {
        'label': 'Items Updated',
        'extractor': lambda e: e['method'] == 'POST' and (e['path'].startswith('/bulk-action/') or e['path'].startswith('/repost') or e['path'].startswith('/edit-item') or e['path'].startswith('/delete-item') or e['path'].startswith('/marksold')),
    },
}

class AnalyticsForm(forms.Form):
    metric_y = forms.ChoiceField(label="Y-axis", choices=[(k, METRICS[k]['label']) for k in METRICS])
    start_time = forms.DateTimeField(label="From", initial=lambda: timezone.now() - timedelta(days=7))
    end_time = forms.DateTimeField(label="To", initial=lambda: timezone.now())
    buckets = forms.IntegerField(label="# of points", min_value=2, max_value=1000, initial=84)
    show_map = forms.BooleanField(label="Show Map", required=False, initial=True)
    map_window = forms.IntegerField(label="Map: last N minutes", min_value=1, initial=10080)

def parse_log_line(line):
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 9:
        return None
    ts_str, method, path, person, ip, os_, browser, lat_part, lon_part = parts[:9]

    try:
        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        ts = timezone.make_aware(ts, timezone.get_default_timezone())
    except:
        return None

    def extract_coord(s):
        try:
            return float(s.split(':')[1].strip())
        except:
            return None

    return {
        'timestamp': ts,
        'method': method,
        'person': person,
        'browser': browser,
        'os': os_,
        'ip': ip,
        'path': path,
        'lat': extract_coord(lat_part),
        'lon': extract_coord(lon_part),
    }

def analytics(request):
    form = AnalyticsForm(request.GET or None)
    chart_data = None
    map_points = []
    summary = {}
    os_dist = Counter()
    browser_dist = Counter()
    hourly_hits = [0]*24
    top_paths = Counter()

    if form.is_valid():
        cd = form.cleaned_data
        entries = []
        with open(LOGFILE) as f:
            for line in f:
                e = parse_log_line(line)
                if not e:
                    continue
                if not (cd['start_time'] <= e['timestamp'] <= cd['end_time']):
                    continue
                entries.append(e)

        total_secs = (cd['end_time'] - cd['start_time']).total_seconds()
        step = total_secs / cd['buckets']
        seen = [set() for _ in range(cd['buckets'])]
        counts = [0] * cd['buckets']
        metric = METRICS[cd['metric_y']]

        for e in entries:
            age = (e['timestamp'] - cd['start_time']).total_seconds()
            idx = min(int(age // step), cd['buckets'] - 1)
            val = metric['extractor'](e)
            if isinstance(val, bool):
                if val:
                    counts[idx] += 1
            else:
                seen[idx].add(val)

            os_dist[e['os']] += 1
            browser_dist[e['browser']] += 1
            hourly_hits[e['timestamp'].hour] += 1
            top_paths[e['path']] += 1

        if cd['metric_y'].startswith('unique'):
            counts = [len(s) for s in seen]

        labels = [
            (cd['start_time'] + timedelta(seconds=step * i)).strftime('%H:%M')
            for i in range(cd['buckets'])
        ]
        chart_data = {
            'labels': labels,
            'dataset': {
                'label': metric['label'],
                'data': counts,
            }
        }

        summary = {
            'total_requests': len(entries),
            'returning_visitors': sum(1 for c in Counter(e['ip'] for e in entries).values() if c > 1),
            'os_distribution': dict(os_dist.most_common()),
            'browser_distribution': dict(browser_dist.most_common()),
            'hourly_hits': hourly_hits,
            'top_paths': dict(top_paths.most_common(10))
        }

        if cd['show_map']:
            cutoff = timezone.now() - timedelta(minutes=cd['map_window'])
            recent = [e for e in entries if e['timestamp'] >= cutoff]
            seen_ips = set()
            for e in recent:
                ip = e['ip']
                if ip in seen_ips:
                    continue
                seen_ips.add(ip)
                if e['lat'] is None or e['lon'] is None:
                    continue
                map_points.append({
                    'lat': e['lat'],
                    'lon': e['lon'],
                    'timestamp': e['timestamp'].strftime('%H:%M:%S')
                })

    return render(request, 'bits/analytics.html', {
        'form': form,
        'chart_data': chart_data,
        'map_points': map_points,
        'summary': summary,
        'show_map': form.cleaned_data['show_map'] if form.is_valid() else False,
    })


####THIS PART IS FOR NOTIFICATIONS BRO!!!####


def generate_notification(item_name, price):
    title_options = [
        "🛒 New Item!",
        "✨ Fresh Drop!",
        "🚀 New Product!",
        "🔥 Hot Listing!",
        "🎯 Item Alert!"
    ]

    body_templates = [
        f"{item_name} at {price}!",
        f"Grab {item_name} for {price}!",
        f"Now selling: {item_name} at {price}",
        f"Get your {item_name} – {price}",
        f"Available now: {item_name} for {price}!"
    ]

    notification_title = random.choice(title_options)
    notification_body = random.choice(body_templates)

    return notification_title, notification_body

def send_notification(request, person, item):
    print("✅ Initiating notification...")
    if person.last_notification and (timezone.now() - person.last_notification < timedelta(minutes=NOTIFICATION_COOLDOWN)):
        next_notification_time = person.last_notification + timedelta(minutes=NOTIFICATION_COOLDOWN)
        time_remaining = int((next_notification_time - timezone.now()).total_seconds() // 60)
        print(f"❌ Message Cooldown {time_remaining} minutes")
        messages.warning(request, f"You can only send notifications once in {NOTIFICATION_COOLDOWN} minutes! Please wait {time_remaining} more minutes.")
    else:
        print("✅ Sending notification...")
        person.last_notification = timezone.now()
        person.save()
        campus = person.campus
        if person.email == 'contact@example.com':
            target_persons = Person.objects.filter(campus=campus)
        else:
            target_persons = Person.objects.filter(campus=campus).exclude(email=person.email)
        target_persons = list(target_persons)
        random.shuffle(target_persons)
        threading.Thread(target=send_pushFemail_notification, args=(request, target_persons, person, item)).start()

SUBSCRIPTIONS_FILE = os.path.join(settings.LOG_DIR, 'subscriptions.json')

if os.path.exists(SUBSCRIPTIONS_FILE):
    with open(SUBSCRIPTIONS_FILE, 'r') as f:
        try:
            subscriptions = json.load(f)
        except json.JSONDecodeError:
            subscriptions = []
else:
    subscriptions = []

@csrf_exempt
def save_subscription(request):
    data = json.loads(request.body)

    email = None
    if request.session.get('user_data'):
        email = request.session['user_data'].get('email')

    if not email:
        return JsonResponse({"status": "error", "message": "User not logged in"}, status=401)

    subscriptions = {}

    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            try:
                subscriptions = json.load(f)
                if not isinstance(subscriptions, dict):
                    subscriptions = {}
            except json.JSONDecodeError:
                subscriptions = {}

    subscriptions[email] = data

    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subscriptions, f, indent=2)

    return JsonResponse({"status": "subscription saved"})

def send_email_notification(users, subject, context, template_name):
    for user in users:
        html_content = render_to_string(template_name, context)

        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email='contact@example.com',
            to=[user.email],
        )
        email.content_subtype = "html"
        email.send()

def send_pushFemail_notification(request, target_persons, owner, item):
    symbol = '₹'
    if owner.campus == 'DUB':
        symbol = 'AED'
    price = f"{symbol}{item.price}"
    notif_title, notif_body = generate_notification(item.name, price)
    first_image = item.images.first()
    first_image_url = first_image.image.url if first_image else None
    first_image_url = request.build_absolute_uri(first_image_url)
    print("First image URL:", first_image_url)
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        return
    with open(SUBSCRIPTIONS_FILE, 'r') as f:
        subscriptions = json.load(f)
    payload = json.dumps({
        "title": notif_title,
        "body": notif_body,
        "image": first_image_url,
    })
    updated = False
    def email_person(person):
        if person.is_subscribed:
            token = generate_unsubscribe_token(person)
            context = {
                "user_name": person.name,
                "unsubscribe_token": token,
                "item_image_url": first_image_url,
                "owner_name": owner.name,
                "add_product_link": request.build_absolute_uri(reverse('add_product')),
                "feedback_link": request.build_absolute_uri(reverse('feedback')),
                "item": item,
                "item_link": request.build_absolute_uri(reverse('item_detail' , args=[item.id])),
                "unsubscribe_link": request.build_absolute_uri(reverse('unsubscribe', args=[generate_unsubscribe_token(person)])),
            }
            try:
                send_email_notification([person], notif_title, context, "bits/emailtemplate.html")
                print("✅ Email sent successfully to", person.email, "with token:", token)
            except:
                print("❌ Email sending failed for", person.email)
    email_users = []

    for person in target_persons:
        subscription = subscriptions.get(person.email)
        if not subscription:
            # email_users.append(person)
            continue
        try:
            # raise WebPushException("Random")
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
                content_encoding='aes128gcm',
                ttl=36000
            )
            print(f"✅ Push sent successfully to {person.email}")
        except WebPushException as ex:
            print(f"❌ Web push failed for {person.email}: {repr(ex)}")
            subscriptions.pop(person.email, None)
            updated = True
            # email_users.append(person)

    if updated:
        with open(SUBSCRIPTIONS_FILE, 'w') as f:
            json.dump(subscriptions, f, indent=2)
        print("✅ Cleaned up dead subscriptions.")

    # for p in email_users:
    #     email_person(p)

    print("✅ Notification process completed.")

def send_push_notifications_to_all(title, body):
    payload = json.dumps({
        "title": title,
        "body": body
    })
    print("Payload being sent:", payload)

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
                content_encoding='aes128gcm'
            )
            print("Push sent successfully.")
        except WebPushException as ex:
            print("Web push failed:", repr(ex))


LOGFILE = os.path.join(settings.LOG_DIR, 'request_logs.log')


### THIS IS WHERE THE REAL SHIT STARTS ###


@csrf_exempt
def sign_in(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        return HttpResponseRedirect(reverse('home'))
    else:
        return render(request, 'bits/sign-in.html')

@csrf_exempt
def auth_receiver(request):
    token = request.POST['credential']
    user_data = id_token.verify_oauth2_token(token, requests.Request(), os.environ['GOOGLE_OAUTH_CLIENT_ID'], clock_skew_in_seconds = 10)
    request.session['user_data'] = user_data
    if not Person.objects.filter(email=user_data['email']).exists():
        person = Person(email=user_data['email'], name=user_data['name'])
        person.save()
    if user_data['email'] in banned_list:
        messages.error(request, "YOU'RE BANNED, CONTACT ADMIN TO RESOLVE!!")
        return render(request, 'bits/sign-in.html')
    return redirect('home')

def sign_out(request):
    del request.session['user_data']
    return HttpResponseRedirect(reverse('sign_in'))

install_logger = logging.getLogger("install_logger")

@csrf_exempt
def log_install(request):
    if request.method == "POST":
        ip = (
            request.META.get('HTTP_CF_CONNECTING_IP')
            or request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0]
            or request.META.get('REMOTE_ADDR')
        )
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(ua_string)
        os = f"{user_agent.os.family} {user_agent.os.version_string}"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        person = Person.objects.get(email=request.session.get('user_data')['email'])
        install_logger.info(f"{timestamp} | INSTALL | {person.id} - {person.name} | IP: {ip} | OS: {os}")
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)

def add_product(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        person = Person.objects.get(email=request.session.get('user_data')['email'])

        if request.method == 'POST':
            form = ItemForm(request.POST, request.FILES, user=person)

            if form.is_valid():
                item = form.save(commit=False)
                item.seller = person

                whatsapp_number = form.cleaned_data.get('phone')
                hostel = form.cleaned_data.get('hostel')

                if whatsapp_number:
                    person.phone = whatsapp_number
                    person.save()

                if hostel:
                    person.hostel = hostel
                    person.save()

                item.hostel = person.hostel
                category = form.cleaned_data.get('category')
                item.category = category

                item.save()
                images = request.FILES.getlist('images')
                image_order = []
                if 'image_order' in request.POST and request.POST['image_order']:
                    try:
                        image_order = json.loads(request.POST['image_order'])
                    except Exception as e:
                        image_order = list(range(len(images)))
                else:
                    image_order = list(range(len(images)))
                if images:
                    for index in range(len(image_order)):
                        try:
                            image_file = images[int(image_order[index])]
                            image_instance = Image(
                                item=item,
                                image=image_file,
                                display_order=index
                            )
                            image_instance.save()
                        except IndexError:
                            print(f"IndexError: Invalid index in image_order for uploaded images.")

                elif 'image' in request.FILES:
                    image_file = request.FILES['image']
                    image_instance = Image(item=item, image=image_file, display_order=0)
                    image_instance.save()
                messages.success(request, "Product added successfully!")
                send_notification(request, person, item)
                return redirect('my_listings')
            else:
                messages.error(request, "Please correct the errors below.")
                return render(request, 'bits/add_product.html', {'form': form})

        else:
            form = ItemForm(user=person)
            form.setdata(person.hostel, person.phone)

        return render(request, 'bits/add_product.html', {'form': form})
    else:
        return HttpResponseRedirect(reverse('sign_in'))

    
def home(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        current_user = Person.objects.get(email=request.session.get('user_data')['email'])
        
        category = request.GET.get('c')
        query = request.GET.get('q')
        sort_method = request.GET.get('sort')
        selected_campus = request.GET.get('campus')
        
        items_query = Item.objects.all()
        
        if selected_campus == 'ALL':
            selected_campus = 'ALL'
            campus_filter = None
        elif selected_campus in ['GOA', 'HYD', 'PIL', 'DUB']:
            items_query = items_query.filter(seller__campus=selected_campus)
            campus_filter = selected_campus
        elif not selected_campus:
            if current_user.campus in ['GOA', 'HYD', 'PIL', 'DUB']:
                items_query = items_query.filter(seller__campus=current_user.campus)
                selected_campus = current_user.campus
                campus_filter = current_user.campus
            else:
                selected_campus = 'ALL'
                campus_filter = None
        
        if category:
            items_query = items_query.filter(Q(category__id=category))
        
        if query:
            items_query = items_query.filter(
                Q(name__icontains=query) | 
                Q(hostel__name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        
        all_items = items_query
        
        categories = Category.objects.all()
        categories_with_counts = []
        
        all_items_count = all_items.count()
        
        for cat in categories:
            cat_items = Item.objects.filter(category=cat)
            if campus_filter:
                cat_items = cat_items.filter(seller__campus=campus_filter)
            
            cat_dict = {
                'id': cat.id,
                'name': cat.name,
                'icon_class': cat.icon_class,
                'item_count': cat_items.count()
            }
            categories_with_counts.append(cat_dict)
        
        categories_with_counts = sorted(categories_with_counts, key=lambda x: x['item_count'], reverse=True)
        
        items = helper.items_sort(items_query, sort_method)
        
        items_per_page = 16
        paginator = Paginator(list(items), items_per_page)
        page = request.GET.get('page')
        
        try:
            paginated_items = paginator.page(page)
        except PageNotAnInteger:
            paginated_items = paginator.page(1)
        except EmptyPage:
            paginated_items = paginator.page(paginator.num_pages)
        for c in categories:
            if selected_campus != 'ALL':
                c.item_count = Item.objects.filter(category=c, seller__campus=selected_campus).count()
            else:
                c.item_count = items_query.filter(category=c).count()
        return render(request, "bits/home.html", {
            'user': current_user,
            'items': paginated_items,
            'is_paginated': True,
            'page_obj': paginated_items,
            'paginator': paginator,
            'selected_campus': selected_campus,
            'categories_with_counts': categories_with_counts,
            'all_items_count': all_items_count,
            'categories': categories,
            'total_items_count': len(Item.objects.all()) if selected_campus == 'ALL' else len(Item.objects.filter(seller__campus=selected_campus)),
        })
    else:
        return HttpResponseRedirect(reverse('sign_in'))
def item_detail(request, id):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        item = get_object_or_404(Item, id=id)
        
        similar_items = Item.objects.filter(
            hostel=item.hostel
        ).exclude(
            id=item.id
        ).order_by('-updated_at')[:5]
        
        context = {
            'item': item,
            'similar_items': similar_items,
        }
        
        return render(request, 'bits/item_detail.html', context)
    else:
        return redirect('sign_in')

def my_listings(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        person = Person.objects.get(email=request.session.get('user_data')['email'])
        listings = helper.items_sort(Item.objects.filter(seller=person))
        return render(request, 'bits/listings.html', {'listings': listings})
    else:
        return HttpResponseRedirect(reverse('sign_in'))

def delete_item(request, id):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        item = get_object_or_404(Item, id=id)
        if item.seller.email == request.session.get('user_data')['email']:
            images = Image.objects.filter(item=item)
            for image in images:
                image.image.delete(save=False)
                image.delete()
            item.delete()
        return redirect('my_listings')
    else:
        return HttpResponseRedirect(reverse('sign_in'))

def edit_item(request, id):
    try:
        item = Item.objects.get(id=id)
        
        if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
            person = Person.objects.get(email=request.session.get('user_data')['email'])
            
            if item.seller != person:
                messages.error(request, "You can only edit your own items.")
                return redirect('home')
                
            existing_images = [
                {
                    'id': img.id,
                    'url': img.image.url,
                    'display_order': img.display_order
                } for img in item.images.all().order_by('display_order')
            ]
            
            existing_images_json = json.dumps(existing_images)
            
            if request.method == 'POST':
                form = ItemForm(request.POST, request.FILES, instance=item, user=person)
                
                if form.is_valid():
                    updated_item = form.save(commit=False)
                    
                    whatsapp_number = form.cleaned_data.get('phone')
                    hostel = form.cleaned_data.get('hostel')
                    
                    if whatsapp_number:
                        person.phone = whatsapp_number
                        person.save()
                    
                    if hostel:
                        person.hostel = hostel
                        person.save()
                    
                    updated_item.hostel = person.hostel
                    updated_item.save()
                    
                    try:
                        image_order_raw = request.POST.get('image_order', '{}')
                        image_order_data = json.loads(image_order_raw)
                        
                        existing_images = list(item.images.all())
                        
                        if isinstance(image_order_data, dict):
                            existing_ids = image_order_data.get('existing', [])

                            to_delete = [img for img in existing_images if img.id not in existing_ids]
                            for img in to_delete:
                                img.image.delete(save=False)
                                img.delete()
                            
                            new_images = request.FILES.getlist('images')
                            new_image_order = image_order_data.get('new', list(range(len(new_images))))
                            
                            final_order = []
                            
                            for img in item.images.all():
                                img.display_order = -1
                                img.save()
                            
                            for idx, img_id in enumerate(existing_ids):
                                try:
                                    img = Image.objects.get(id=img_id, item=item)
                                    img.display_order = idx
                                    img.save()
                                    final_order.append(('existing', img_id))
                                except Image.DoesNotExist:
                                    continue
                            
                            for idx, img_idx in enumerate(new_image_order):
                                if img_idx < len(new_images):
                                    new_img = Image.objects.create(
                                        item=item,
                                        image=new_images[img_idx],
                                        display_order=len(existing_ids) + idx
                                    )
                                    final_order.append(('new', new_img.id))

                            if 'combined_order' in image_order_data:
                                combined_order = image_order_data['combined_order']
                                all_images = list(item.images.all())
                                
                                for img in all_images:
                                    img.display_order = -1
                                    img.save()
                                
                                for idx, img_info in enumerate(combined_order):
                                    img_type, img_id = img_info
                                    if img_type == 'existing':
                                        try:
                                            img = Image.objects.get(id=img_id, item=item)
                                            img.display_order = idx
                                            img.save()
                                        except Image.DoesNotExist:
                                            continue
                        else:
                            for img in existing_images:
                                img.image.delete(save=False)
                                img.delete()
                            new_images = request.FILES.getlist('images')
                            for idx, img in enumerate(new_images):
                                Image.objects.create(
                                    item=item,
                                    image=img,
                                    display_order=idx
                                )
                    
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                    messages.success(request, "Item updated successfully!")
                    send_notification(request, person, item)
                    return redirect('my_listings')
                else:
                    return render(request, 'bits/add_product.html', {
                        'form': form,
                        'item': item,
                        'existing_images_json': existing_images_json
                    })
            else:
                form = ItemForm(instance=item, user=person)
                
                return render(request, 'bits/add_product.html', {
                    'form': form,
                    'item': item,
                    'existing_images_json': existing_images_json
                })
        else:
            return redirect('sign_in')
    except Item.DoesNotExist:
        messages.error(request, "Item not found.")
        return redirect('home')

def feedback(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        person = Person.objects.get(email=request.session.get('user_data')['email'])
    else:
        person = None

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.person = person
            feedback.save()
            
            images = request.FILES.getlist('images')
            for image in images:
                FeedbackImage.objects.create(
                    feedback=feedback,
                    image=image
                )

            messages.success(request, "Thank you for your feedback!")
            if person:
                return redirect('home')
            return redirect('feedback')
    else:
        form = FeedbackForm()
    return render(request, 'bits/feedback.html', {'form': form})

def marksold(request, id):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        if Item.objects.filter(id=id).exists():
            item = Item.objects.get(id=id)
            item.is_sold = True
            item.save()
        return redirect('my_listings')
    else:
        return redirect("sign_in")
    
def about_us(request):
    return render(request, 'bits/about.html')

def categories(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        return render(request, 'bits/categories.html', {'categories': Category.objects.all()})
    else:
        return redirect('sign_in')

def bypass(request):  
    category = request.GET.get('c')
    query = request.GET.get('q')
    sort_method = request.GET.get('sort')
    selected_campus = request.GET.get('campus')
    
    items_query = Item.objects.all()
    
    if selected_campus == 'ALL':
        selected_campus = 'ALL'
        campus_filter = None
    elif selected_campus in ['GOA', 'HYD', 'PIL', 'DUB']:
        items_query = items_query.filter(seller__campus=selected_campus)
        campus_filter = selected_campus
    elif not selected_campus:
        selected_campus = 'ALL'
        campus_filter = None
    
    if category:
        items_query = items_query.filter(Q(category__id=category))
    
    if query:
        items_query = items_query.filter(
            Q(name__icontains=query) | 
            Q(hostel__name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    all_items = items_query
    
    categories = Category.objects.all()
    categories_with_counts = []
    
    all_items_count = all_items.count()
    
    for cat in categories:
        cat_items = Item.objects.filter(category=cat)
        if campus_filter:
            cat_items = cat_items.filter(seller__campus=campus_filter)
        
        cat_dict = {
            'id': cat.id,
            'name': cat.name,
            'icon_class': cat.icon_class,
            'item_count': cat_items.count()
        }
        categories_with_counts.append(cat_dict)
    
    categories_with_counts = sorted(categories_with_counts, key=lambda x: x['item_count'], reverse=True)
    
    items = helper.items_sort(items_query, sort_method)
    
    items_per_page = 16
    paginator = Paginator(list(items), items_per_page)
    page = request.GET.get('page')
    
    try:
        paginated_items = paginator.page(page)
    except PageNotAnInteger:
        paginated_items = paginator.page(1)
    except EmptyPage:
        paginated_items = paginator.page(paginator.num_pages)
    for c in categories:
        if selected_campus != 'ALL':
            c.item_count = Item.objects.filter(category=c, seller__campus=selected_campus).count()
        else:
            c.item_count = items_query.filter(category=c).count()
    return render(request, "bits/home.html", {
        'user': None,
        'items': paginated_items,
        'is_paginated': True,
        'page_obj': paginated_items,
        'paginator': paginator,
        'selected_campus': selected_campus,
        'categories_with_counts': categories_with_counts,
        'all_items_count': all_items_count,
        'categories': categories,
        'total_items_count': len(Item.objects.all()) if selected_campus == 'ALL' else len(Item.objects.filter(seller__campus=selected_campus)),
    })

def custom_page_not_found(request, exception):
    return render(request, 'bits/404.html', status=404)

def custom_server_error(request):
    return render(request, 'bits/500.html', status=500)

def repost(request, id):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        person = Person.objects.get(email=request.session.get('user_data')['email'])
        item = get_object_or_404(Item, id=id)
        
        if item.seller != person:
            messages.error(request, "You can only repost your own items.")
            return redirect('home')

        item.is_sold = False
        item.hostel = person.hostel
        item.save(change_time=True)
        source = request.GET.get('source')
        messages.success(request, f"'{item.name}' has been reposted successfully!")
        send_notification(request, person, item)
        if source == 'home':
            return redirect('home')
        else:
            return redirect('my_listings')
    else:
        return redirect('sign_in')

@csrf_exempt
def bulk_action(request, action):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        if request.method == 'POST':
            person = Person.objects.get(email=request.session.get('user_data')['email'])
            selected_items = request.POST.get('selected_items', '').split(',')
            
            items = Item.objects.filter(id__in=selected_items, seller=person)
            
            if not items:
                messages.error(request, "No valid items were selected.")
                return redirect('my_listings')
            
            if action == 'repost':
                count = 0
                for item in items:
                    item.is_sold = False
                    item.hostel = person.hostel
                    item.save()
                    count += 1
                send_notification(request, person, item)
                messages.success(request, f"Successfully reposted {count} item(s).")

            elif action == 'toggle_sold':
                count = 0
                for item in items:
                    item.is_sold = not item.is_sold
                    item.save(change_time=False)
                    count += 1
                messages.success(request, f"Successfully toggled sold status for {count} item(s).")
                
            elif action == 'delete':
                count = 0
                for item in items:
                    images = Image.objects.filter(item=item)
                    for image in images:
                        image.image.delete(save=False)
                        image.delete()
                    item.delete()
                    count += 1
                messages.success(request, f"Successfully deleted {count} item(s).")
            
            return redirect('my_listings')
    else:
        return redirect('sign_in')

def terms(request):
    return render(request, 'bits/terms.html')

@csrf_exempt
def api_items(request):
    items = Item.objects.filter(is_sold=False).select_related('seller', 'hostel', 'category').prefetch_related('images').order_by('-added_at')

    data = []

    for item in items:
        first_image = item.images.first()
        image_url = first_image.image.url if first_image else ""

        data.append({
            "id": item.id,
            "itemName": item.name,
            "itemImage": request.build_absolute_uri(image_url),
            "itemPrice": int(item.price),
            "sellerName": item.seller.name,
            "sellerHostel": item.hostel.name,
            "dateAdded": item.added_at.isoformat(),
            "contactNumber": item.phone or item.seller.phone,
            "category": item.category.name,
            "campus": item.seller.campus,
            "sellerEmail": item.seller.email,
            "description": item.description,
            "issold": item.is_sold,
        })

    return JsonResponse(data, safe=False)

@csrf_exempt
def api_item_images(request, id):
    try:
        item = Item.objects.get(id=id)
        images = item.images.all()
        image_urls = [request.build_absolute_uri(img.image.url) for img in images]
        return JsonResponse({"item_id": id, "images": image_urls})
    except Item.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

@csrf_exempt
def api_update_item(request, id):
    if request.method == "PUT":
        try:
            item = Item.objects.get(id=id)
        except Item.DoesNotExist:
            return JsonResponse({"error": "Item not found"}, status=404)
        try:
            data = json.loads(request.body)
            new_status = data.get("issold")
            if new_status is None:
                return JsonResponse({"error": "Missing 'issold' in body"}, status=400)
            item.is_sold = bool(new_status)
            item.save()
            return JsonResponse({"id": item.id, "issold": item.is_sold})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    elif request.method == "DELETE":
        try:
            item = Item.objects.get(id=id)
        except Item.DoesNotExist:
            return JsonResponse({"error": "Item not found"}, status=404)
        images = item.images.all()
        for image in images:
            image.image.delete(save=False)
            image.delete()
        item.delete()
        return JsonResponse({"status": "deleted", "id": id})
    else:
        return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def api_feedback(request):
    if request.method == "POST":
        try:
            description = request.POST.get('description', '')
            images = request.FILES.getlist('images')
            feedback = Feedback.objects.create(description=description)
            for image in images:
                FeedbackImage.objects.create(feedback=feedback, image=image)
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid method"}, status=405)