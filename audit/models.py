from django.conf import settings
from django.db import models


class AuditSession(models.Model):
    receipt_approval = models.OneToOneField(
        'receipts.ReceiptApproval',
        on_delete=models.CASCADE,
        related_name='audit_session',
    )
    audit_started_at = models.DateTimeField(auto_now_add=True)
    audit_completed_at = models.DateTimeField(null=True, blank=True)
    audit_duration_ms = models.IntegerField(null=True, blank=True)
    policy_version_used = models.ForeignKey(
        'policies.PolicyDocument',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_sessions',
    )
    total_rules_checked = models.IntegerField(default=0)
    rules_matched = models.IntegerField(default=0)
    rules_flagged = models.IntegerField(default=0)

    def __str__(self):
        return f"AuditSession {self.pk} for approval {self.receipt_approval_id}"


class AuditDecision(models.Model):
    class DecisionStatus(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        FLAGGED = 'flagged', 'Flagged'
        REJECTED = 'rejected', 'Rejected'

    audit_session = models.OneToOneField(
        AuditSession,
        on_delete=models.CASCADE,
        related_name='decision',
    )
    final_status = models.CharField(max_length=20, choices=DecisionStatus.choices)
    approval_confidence_score = models.FloatField()
    generated_explanation = models.TextField()
    flagged_issues = models.JSONField(null=True, blank=True)
    decision_made_by_system = models.BooleanField(default=True)
    manually_overridden_at = models.DateTimeField(null=True, blank=True)
    manually_overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='overridden_audit_decisions',
    )
    override_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AuditDecision {self.final_status} for session {self.audit_session_id}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
        ('overridden', 'Overridden'),
        ('escalated', 'Escalated'),
    ]

    audit_decision = models.ForeignKey(
        AuditDecision,
        on_delete=models.CASCADE,
        related_name='logs',
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_actions',
    )
    action_timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)

    def __str__(self):
        return f"AuditLog {self.action} for decision {self.audit_decision_id}"
