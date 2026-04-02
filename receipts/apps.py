from django.apps import AppConfig


class ReceiptsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "receipts"

    def ready(self):
        # Import inside the method to avoid "AppRegistryNotReady" errors
        from .ocr_processor import ReceiptOCRProcessor 
        
        # This runs exactly once when Django starts
        ReceiptOCRProcessor.configure()