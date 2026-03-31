from django.shortcuts import render

from employees.models import Company, EmployeeProfile
from receipts.models import ReceiptUpload
from policies.models import PolicyDocument, PolicyRule
from audit.models import AuditDecision
from notifications.models import Notification


def home(request):
    context = {
        'company_count': Company.objects.count(),
        'employee_count': EmployeeProfile.objects.count(),
        'recent_receipts': ReceiptUpload.objects.order_by('-upload_timestamp')[:5],
        'active_policies': PolicyDocument.objects.filter(is_active=True).order_by('-effective_date')[:5],
        'recent_decisions': AuditDecision.objects.order_by('-created_at')[:5],
    }
    return render(request, 'home.html', context)


def receipt_list(request):
    uploads = ReceiptUpload.objects.select_related('employee__user').order_by('-upload_timestamp')[:25]
    return render(request, 'receipts.html', {'uploads': uploads})


def policy_list(request):
    policies = PolicyDocument.objects.order_by('-effective_date')[:25]
    rules = PolicyRule.objects.order_by('-created_at')[:25]
    return render(request, 'policies.html', {'policies': policies, 'rules': rules})


def audit_dashboard(request):
    decisions = AuditDecision.objects.order_by('-created_at')[:25]
    return render(request, 'audit.html', {'decisions': decisions})


def notification_list(request):
    notifications = Notification.objects.order_by('-created_at')[:25]
    return render(request, 'notifications.html', {'notifications': notifications})
