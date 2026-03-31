from django.conf import settings
from django.db import models


class Notification(models.Model):
    DELIVERY_METHOD_CHOICES = [
        ('email', 'Email'),
        ('dashboard', 'Dashboard'),
        ('both', 'Both'),
    ]
    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    audit_decision = models.ForeignKey(
        'audit.AuditDecision',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification {self.pk} to {self.recipient.username}"


class NotificationTemplate(models.Model):
    DEFAULT_DELIVERY_METHOD_CHOICES = [
        ('email', 'Email'),
        ('dashboard', 'Dashboard'),
        ('both', 'Both'),
    ]

    name = models.CharField(max_length=100, unique=True)
    subject_template = models.CharField(max_length=255)
    body_template = models.TextField()
    default_delivery_method = models.CharField(max_length=20, choices=DEFAULT_DELIVERY_METHOD_CHOICES)

    def __str__(self):
        return self.name
