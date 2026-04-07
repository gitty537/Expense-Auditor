from celery import shared_task
from .models import ReceiptUpload, ExtractedReceiptData, ReceiptApproval
from .ocr_processor import ReceiptOCRProcessor
from audit.models import AuditSession, AuditDecision, PreAuthorisationForm
from policies.models import PolicyDocument, PolicyRule
from notifications.utils import send_verification_notifications
from django.utils import timezone
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@shared_task
def process_receipt_ocr(receipt_upload_id):
    """
    Async Celery task: Extract OCR data and enforce company policy
    """
    try:
        receipt = ReceiptUpload.objects.get(id=receipt_upload_id)
        receipt.processing_status = 'processing'
        receipt.save()
        
        file_path = receipt.original_file.path
        quality = ReceiptOCRProcessor.assess_quality(file_path)
        
        # 1. OCR Extraction
        structured_data = ReceiptOCRProcessor.extract_structured_data(file_path)
        raw_text = structured_data['raw_text']
        ocr_confidence = structured_data['average_confidence'] / 100.0  # 0-1 scale
        
        # 2. Field & Category Parsing
        fields = ReceiptOCRProcessor.parse_receipt_fields(raw_text)
        
        # Determine amount and date (use extracted or user-provided)
        extracted_amount = float(fields['total_amount'] or 0)
        final_amount = extracted_amount if extracted_amount > 0 else 0
        final_date = fields['transaction_date'] or receipt.expense_date or datetime.now().date()
        
        # 3. Save Extracted Data
        extracted = ExtractedReceiptData.objects.create(
            receipt_upload=receipt,
            merchant_name=fields['merchant_name'],
            transaction_date=final_date,
            claimed_expense_date=receipt.expense_date or final_date,
            total_amount=final_amount,
            currency_code=fields.get('currency_code', 'USD'),
            line_items={},
            ocr_confidence_score=ocr_confidence,
            raw_ocr_text=raw_text,
            # image_quality_score=quality['overall_score']  # Removed as it's handled in ReceiptUpload
        )
        
        # Update receipt with image quality
        receipt.image_quality_score = quality['overall_score']
        receipt.save()

        # 4. Create ReceiptApproval (needed for AuditSession)
        approval = ReceiptApproval.objects.create(
            extracted_data=extracted,
            expense_category=fields['category'] if fields['category'] in ['meals', 'transport', 'lodging', 'entertainment', 'other'] else 'other',
            business_purpose=receipt.reason or "No reason provided",
            claimed_by=receipt.employee
        )

        # 5. Policy Verification & Classification
        status = 'approved'
        explanation = "Passes all policy checks."
        flagged_issues = []

        category = fields['category']
        amount = float(final_amount)
        active_policy = None
        rules_checked = 0

        # ── CONTENT VALIDATION ────────────────────────────────────────────────
        # Reject immediately if receipt has insufficient text content
        word_count = len([w for w in raw_text.split() if w.strip()])
        if word_count < 3:
            status = 'rejected'
            explanation = (
                "Receipt rejected: Insufficient text extracted from image. "
                "The receipt appears to be blank or contains no readable text. "
                "Please upload a clear receipt image with visible merchant, date, and amount information."
            )
            flagged_issues = [
                f"Blank or unreadable receipt: Only {word_count} words extracted from image."
            ]
        
        # ── HARD GATE ────────────────────────────────────────────────────────
        # Reject immediately if the employee has no approved pre-authorisation.
        # The AI is never called in this case.
        if status == 'approved':
            pre_auths = PreAuthorisationForm.objects.filter(
                employee=receipt.employee, status='approved'
            )

            if not pre_auths.exists():
                status = 'rejected'
                explanation = (
                    "Receipt rejected: No approved pre-authorisation form on file "
                    "for this employee. An Expense Pre-Authorisation must be "
                    "submitted and approved by the Finance Auditor before any "
                    "expense claim will be accepted."
                )
                flagged_issues = [
                    "No approved pre-authorisation form exists for this employee."
                ]
            else:
                approved_reasons = "\n".join(
                    [f"- {f.expense_reason} (Est: £{f.estimated_amount})"
                     for f in pre_auths]
                )

                # Fetch the active policy document
                active_policy = PolicyDocument.objects.filter(is_active=True).first()

                if active_policy:
                    import fitz
                    from google import genai
                    from google.genai import types
                    import json

                    try:
                        # Extract policy text (cap at 10 000 chars to save tokens)
                        pdf_doc = fitz.open(active_policy.pdf_file.path)
                        policy_text = ""
                        for page in pdf_doc:
                            policy_text += page.get_text()
                            if len(policy_text) > 10000:
                                break

                        client = genai.Client()

                        prompt = f"""
                        You are an expense auditing AI. Check if this receipt complies with the company policy.

                        Policy Document Text:
                        {policy_text}

                        The employee MUST have a pre-approved reason matching the reason they submitted for this receipt.
                        Here are the approved Pre-Authorization reasons on file for this employee:
                        ---
                        {approved_reasons}
                        ---

                        Receipt Stated Reason: {receipt.reason}
                        Extracted Receipt Data:
                        {raw_text}

                        Category identified: {category}
                        Total Amount: {amount}

                        Verify two things:
                        1. Does the receipt match the rules in the Policy Document?
                        2. Does the Receipt Stated Reason explicitly match one of the Pre-Authorization reasons on file? If it doesn't match, you MUST "reject" or "flag" the claim.

                        Reply ONLY with valid JSON in this exact format:
                        {{"status": "approved" | "flagged" | "rejected", "explanation": "Brief reasoning", "issues": ["issue 1"]}}
                        """

                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                            ),
                        )

                        result = json.loads(response.text)

                        if result.get("status") in ['approved', 'flagged', 'rejected']:
                            status = result["status"]
                            explanation = result.get(
                                "explanation",
                                "AI analyzed the receipt against company policy"
                            )
                            flagged_issues.extend(result.get("issues", []))
                            rules_checked += len(result.get("issues", [])) + 1

                    except Exception as e:
                        logger.error(f"GenAI processing failed: {str(e)}")
                        flagged_issues.append(f"AI Policy check unavailable: {str(e)}")
                        status = 'flagged'

        if receipt.is_potential_duplicate:
            flagged_issues.append("This specific receipt file has been uploaded before.")
            if status == 'approved':
                status = 'flagged'
                explanation = (
                    "Flagged: Potential duplicate file detected. "
                    "The receipt passed policy checks, but it appears to be a duplicate upload "
                    "and requires manual review."
                )

        # Factor in OCR confidence
        if ocr_confidence < 0.7 and status == 'approved':
            status = 'flagged'
            flagged_issues.append(f"Low OCR confidence ({int(ocr_confidence * 100)}%).")
            explanation = "Flagged: OCR data requires manual verification due to low confidence."

        # 6. Create Audit Record
        session = AuditSession.objects.create(
            receipt_approval=approval,
            policy_version_used=active_policy,
            total_rules_checked=rules_checked,
            rules_flagged=len(flagged_issues)
        )
        
        decision = AuditDecision.objects.create(
            audit_session=session,
            final_status=status,
            approval_confidence_score=ocr_confidence,
            generated_explanation=explanation,
            flagged_issues={'issues': flagged_issues}
        )
        
        # 7. Finalize Receipt Status
        receipt.processing_status = ReceiptUpload.ProcessingStatus.COMPLETED
        receipt.save()
        
        # 8. Notify Employee and Admins
        send_verification_notifications(decision)
        
        logger.info(f"OCR & Policy check completed: {status} for receipt {receipt_upload_id}")
        return {'success': True, 'status': status, 'issues': flagged_issues}
    
    except Exception as e:
        receipt.processing_status = 'failed'
        receipt.processing_error_message = str(e)
        receipt.save()
        logger.error(f"OCR failed for receipt {receipt_upload_id}: {str(e)}")
        raise
