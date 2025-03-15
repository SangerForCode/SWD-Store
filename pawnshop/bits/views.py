import os
import json
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests
from django.contrib import messages
from .models import *
from .forms import *
from . import helper
from django.db.models import Q

banned_list = []

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
    if user_data['email'].split('@')[1] != 'goa.bits-pilani.ac.in':
        messages.error(request, "Please use Goa Campus email ID. 🙏🏼")
        return redirect('sign_in')
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
                return redirect('my_listings')
            else:
                messages.error(request, "Please correct the errors below.")
                return render(request, 'bits/add_product.html', {'form': form})

        else:
            form = ItemForm(user=person)

        return render(request, 'bits/add_product.html', {'form': form})
    else:
        return HttpResponseRedirect(reverse('sign_in'))

def home(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        try:
            hostel = request.GET.get('hostel_side')
            items = helper.items_sort(Item.objects.filter(Q(hostel__name__icontains=hostel)))
        except:
            try:
                query = request.GET.get('q')
                items = helper.items_sort( 
                    Item.objects.filter(
                    Q(name__icontains=query) | 
                    Q(hostel__name__icontains=query) |
                    Q(description__icontains=query)
                ))
            except:
                items = helper.items_sort(Item.objects.all())
            
        return render(request, "bits/home.html", {'items': list(items)})
    else:
        return HttpResponseRedirect(reverse('sign_in'))
    
def item_detail(request, id):
    item = get_object_or_404(Item, id=id)
    
    similar_items = Item.objects.filter(
        hostel=item.hostel
    ).exclude(
        id=item.id
    ).order_by('-added_at')[:5]
    
    context = {
        'item': item,
        'similar_items': similar_items,
    }
    
    return render(request, 'bits/item_detail.html', context)

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
                        existing_image_ids = [img.id for img in existing_images]
                        
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
                return redirect('home')
        else:
            form = FeedbackForm()
            
        return render(request, 'bits/feedback.html', {'form': form})
    else:
        return redirect('sign_in')

def feedback(request):
    if request.session.get('user_data') and Person.objects.filter(email=request.session.get('user_data')['email']).exists():
        person = Person.objects.get(email=request.session.get('user_data')['email'])
        
        if request.method == 'POST':
            form = FeedbackForm(request.POST)
            
            if form.is_valid():
                feedback = form.save(commit=False)
                feedback.person = person
                feedback.save()
                
                # Handle image uploads
                images = request.FILES.getlist('images')
                for image in images:
                    FeedbackImage.objects.create(
                        feedback=feedback,
                        image=image
                    )
                
                messages.success(request, "Thank you for your feedback!")
                return redirect('home')
        else:
            form = FeedbackForm()
            
        return render(request, 'bits/feedback.html', {'form': form})
    else:
        return redirect('sign_in')
