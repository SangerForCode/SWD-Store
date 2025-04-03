from django.apps import AppConfig


class BitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bits'
    def ready(self):
            import logging
            logger = logging.getLogger(__name__)
            try:
                from .item_categorizer import categorizer
                logger.info("Categorizer imported successfully")
            except Exception as e:
                logger.error(f"Error importing categorizer: {str(e)}")