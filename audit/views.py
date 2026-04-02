from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Audit
from .forms import AuditForm

@login_required
def audit_view(request):
    """
    Display audit log with search and filter functionality.
    Only accessible to Finance Manager and Finance Auditor.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager and not user.is_finance_auditor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    
    # Get search query
    query = request.GET.get('q', '')
    
    # Get filter parameters
    action = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    audits = Audit.objects.all().select_related('user')
    
    # Apply search filter
    if query:
        audits = audits.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(action__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Apply action filter
    if action:
        audits = audits.filter(action=action)
    
    # Apply user filter
    if user_filter:
        audits = audits.filter(user_id=user_filter)
    
    # Apply date filters
    if date_from:
        audits = audits.filter(timestamp__date__gte=date_from)
    if date_to:
        audits = audits.filter(timestamp__date__lte=date_to)
    
    # Get unique actions and users for filters
    actions = Audit.ACTION_CHOICES
    users = Employee.objects.all().select_related('user')
    
    context = {
        'audits': audits,
        'query': query,
        'action': action,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'actions': actions,
        'users': users,
        'active_page': 'audit',
    }
    
    return render(request, 'audit.html', context)

@login_required
def audit_detail_view(request, audit_id):
    """
    Display detailed information about a specific audit record.
    Only accessible to Finance Manager and Finance Auditor.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager and not user.is_finance_auditor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    
    audit = get_object_or_404(Audit.objects.select_related('user'), id=audit_id)
    
    context = {
        'audit': audit,
        'active_page': 'audit',
    }
    
    return render(request, 'audit_detail.html', context)
