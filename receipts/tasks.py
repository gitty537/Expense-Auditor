from celery import shared_task
from .models import ReceiptUpload, ExtractedReceiptData
from .ocr_processor import ReceiptOCRProcessor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@shared_task
def process_receipt_ocr(receipt_upload_id):
    """
    Async Celery task: Extract OCR data from uploaded receipt
    """
    try:
        receipt = ReceiptUpload.objects.get(id=receipt_upload_id)
        receipt.processing_status = 'processing'
        receipt.save()
        
        # Get file path
        file_path = receipt.original_file.path
        
        # Assess quality
        quality = ReceiptOCRProcessor.assess_quality(file_path)
        
        # Extract text
        structured_data = ReceiptOCRProcessor.extract_structured_data(file_path)
        raw_text = structured_data['raw_text']
        ocr_confidence = structured_data['average_confidence']
        
        # Parse fields
        fields = ReceiptOCRProcessor.parse_receipt_fields(raw_text)
        
        # Store results
        extracted = ExtractedReceiptData.objects.create(
            receipt_upload=receipt,
            merchant_name=fields['merchant_name'],
            transaction_date=fields['transaction_date'] or datetime.now().date(),
            claimed_expense_date=receipt.expense_date or datetime.now().date(),
            total_amount=fields['total_amount'] or 0,
            currency_code=fields.get('currency_code', 'USD'),
            line_items={},
            ocr_confidence_score=ocr_confidence / 100,  # Convert to 0-1
            raw_ocr_text=raw_text,
            image_quality_score=quality['overall_score']
        )
        
        # Policy Verification
        from policies.models import PolicyRule
        error_sentence = ""
        is_flagged = False
        
        rules = PolicyRule.objects.all()
        for rule in rules:
            if rule.rule_type == 'max_amount':
                try:
                    max_val = float(rule.constraint_value)
                    if float(extracted.total_amount) > max_val:
                        is_flagged = True
                        error_sentence = f"Receipt flagged: Expense amount {extracted.total_amount} {extracted.currency_code} exceeds the company policy maximum of {max_val}."
                        break
                except ValueError:
                    pass
        
        if is_flagged:
            receipt.processing_status = 'failed'
            receipt.processing_error_message = error_sentence
        else:
            receipt.processing_status = 'completed'
            receipt.processing_error_message = "Receipt successfully verified and passed policy checks."
            
        receipt.image_quality_score = quality['overall_score']
        receipt.save()
        
        logger.info(f"OCR completed for receipt {receipt_upload_id}")
        
        return {
            'success': True,
            'merchant': fields['merchant_name'],
            'amount': fields['total_amount'],
            'confidence': ocr_confidence
        }
    
    except Exception as e:
        receipt.processing_status = 'failed'
        receipt.processing_error_message = str(e)
        receipt.save()
        logger.error(f"OCR failed for receipt {receipt_upload_id}: {str(e)}")
        raise