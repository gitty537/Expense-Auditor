from django.conf import settings
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class PolicyDocument(models.Model):
    version = models.CharField(max_length=50, unique=True)
    pdf_file = models.FileField(upload_to='policies/pdfs/', null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_policy_documents',
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending Review'), ('active', 'Active'), ('rejected', 'Rejected')],
        default='pending'
    )
    content = models.TextField(blank=True)
    effective_date = models.DateField()
    deprecation_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    indexed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.version


class PolicyRule(models.Model):
    CATEGORY_CHOICES = [
        ('meals', 'Meals'),
        ('transport', 'Transport'),
        ('lodging', 'Lodging'),
        ('entertainment', 'Entertainment'),
        ('office_supplies', 'Office Supplies'),
        ('training', 'Training'),
        ('gifts', 'Gifts'),
        ('other', 'Other'),
    ]
    REGION_CHOICES = [
        ('New York', 'New York'),
        ('London', 'London'),
        ('Tokyo', 'Tokyo'),
        ('Singapore', 'Singapore'),
        ('Remote', 'Remote'),
        ('Global', 'Global'),
    ]
    RULE_TYPE_CHOICES = [
        ('max_amount', 'Max Amount'),
        ('per_diem', 'Per Diem'),
        ('prohibited', 'Prohibited'),
        ('requires_approval', 'Requires Approval'),
        ('conditional', 'Conditional'),
    ]

    policy_version = models.ForeignKey(
        PolicyDocument,
        on_delete=models.CASCADE,
        related_name='rules',
    )
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    region = models.CharField(max_length=50, choices=REGION_CHOICES)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    constraint_name = models.CharField(max_length=100)
    constraint_value = models.CharField(max_length=255)
    constraint_metadata = models.JSONField(null=True, blank=True)
    description = models.TextField()
    exceptions = models.JSONField(null=True, blank=True)
    referenced_page = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.policy_version.version} - {self.constraint_name}"


class PolicyIndex(models.Model):
    policy_rule = models.OneToOneField(PolicyRule, on_delete=models.CASCADE, related_name='index')
    search_vector = SearchVectorField(null=True, blank=True)
    indexed_content = models.TextField(blank=True)

    def __str__(self):
        return f"Index for {self.policy_rule.constraint_name}"


class PolicyApproval(models.Model):
    policy = models.ForeignKey(
        PolicyDocument,
        on_delete=models.CASCADE,
        related_name='approvals',
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='policy_approvals',
    )
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('policy', 'admin')

    def __str__(self):
        return f"Approval for {self.policy.version} by {self.admin.username}"
