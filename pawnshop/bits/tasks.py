from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Item

@shared_task
def mark_old_items_as_sold():
    threshold = timezone.now() - timedelta(days=60)
    count = Item.objects.filter(is_sold=False, updated_at__lt=threshold).update(is_sold=True)
    return f"{count} items marked as sold"
