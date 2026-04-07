from django.conf import settings
from django.db import models


class ReceiptUpload(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    employee = models.ForeignKey(
        'employees.EmployeeProfile',
        on_delete=models.CASCADE,
        related_name='receipt_uploads',
    )
    original_file = models.FileField(upload_to='receipts/originals/')
    file_size = models.PositiveIntegerField()
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    expense_date = models.DateField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    processing_status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING)
    processing_error_message = models.TextField(null=True, blank=True)
    receipt_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    file_hash = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    is_potential_duplicate = models.BooleanField(default=False)
    image_quality_score = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"ReceiptUpload {self.pk} by {self.employee.user.username}"


class ExtractedReceiptData(models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('GBP', 'GBP'),
        ('JPY', 'JPY'),
        ('EUR', 'EUR'),
        ('SGD', 'SGD'),
    ]

    receipt_upload = models.OneToOneField(ReceiptUpload, on_delete=models.CASCADE, related_name='extracted_data')
    merchant_name = models.CharField(max_length=255)
    transaction_date = models.DateField()
    claimed_expense_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_code = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    line_items = models.JSONField()
    ocr_confidence_score = models.FloatField()
    raw_ocr_text = models.TextField()
    date_mismatch_flag = models.BooleanField(default=False)
    extracted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_receipts',
    )
    manual_corrections = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"ExtractedReceiptData for upload {self.receipt_upload_id}"


class ReceiptApproval(models.Model):
    class ExpenseCategory(models.TextChoices):
        MEALS = 'meals', 'Meals'
        TRANSPORT = 'transport', 'Transport'
        LODGING = 'lodging', 'Lodging'
        ENTERTAINMENT = 'entertainment', 'Entertainment'
        OTHER = 'other', 'Other'

    extracted_data = models.ForeignKey(
        ExtractedReceiptData,
        on_delete=models.CASCADE,
        related_name='approvals',
    )
    expense_category = models.CharField(max_length=50, choices=ExpenseCategory.choices)
    business_purpose = models.TextField()
    claimed_by = models.ForeignKey(
        'employees.EmployeeProfile',
        on_delete=models.CASCADE,
        related_name='receipt_claims',
    )
    claimed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ReceiptApproval {self.pk} for {self.extracted_data.receipt_upload_id}"
