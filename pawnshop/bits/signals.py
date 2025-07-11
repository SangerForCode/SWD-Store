from django.db.models.signals import pre_delete, post_save, post_delete
from django.dispatch import receiver
from .models import Image, Item, Category
from django.core.cache import cache

@receiver(pre_delete, sender=Image)
def delete_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)

@receiver([post_save, post_delete], sender=Item)
def invalidate_item_cache(sender, **kwargs):
    try:
        cache_keys_to_delete = []
        print("Cache invalidated due to Item change")
        
    except Exception as e:
        print(f"Error invalidating cache: {e}")

@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, **kwargs):
    try:
        print("Cache invalidated due to Category change")
    except Exception as e:
        print(f"Error invalidating category cache: {e}")