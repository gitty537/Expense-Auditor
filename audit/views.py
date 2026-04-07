from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import AuditSession, AuditDecision, AuditLog, PreAuthorisationForm
from employees.models import EmployeeProfile

@login_required
def audit_view(request):
    """
    Display audit decisions with search and filter functionality.
    Only accessible to Finance Manager and Finance Auditor.
    """
    user = request.user
    
    # Base authorization for viewing audit logs
    is_audit_authorized = user.roles.filter(role__in=['admin']).exists()
    
    if not is_audit_authorized:
        messages.error(request, "You do not have permission to access the audit dashboard.")
        return redirect('home')
    
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    
    decisions = AuditDecision.objects.all().select_related('audit_session__receipt_approval__claimed_by__user')
    
    if query:
        decisions = decisions.filter(
            Q(generated_explanation__icontains=query) |
            Q(audit_session__receipt_approval__claimed_by__user__username__icontains=query)
        )
    
    if status:
        decisions = decisions.filter(final_status=status)
    
    
    context = {
        'decisions': decisions,
        'query': query,
        'status': status,
        'active_page': 'audit',
    }
    
    return render(request, 'audit.html', context)

@login_required
def audit_detail_view(request, audit_id):
    """
    Display detailed information about a specific audit decision.
    """
    user = request.user
    if not user.roles.filter(role__in=['admin']).exists():
        messages.error(request, "Permission denied.")
        return redirect('home')
        
    decision = get_object_or_404(AuditDecision, id=audit_id)
    
    context = {
        'decision': decision,
        'active_page': 'audit',
    }
    
    return render(request, 'audit_detail.html', context)

@login_required
def pre_auth_submit_view(request):
    """
    Handle submission of pre-authorisation form BEFORE receipt upload.
    """
    if request.method == 'POST':
        expense_reason = request.POST.get('expense_reason', '').strip()
        estimated_amount = request.POST.get('estimated_amount', '0') or '0'

        if not expense_reason:
            messages.error(request, 'Expense reason is required.')
            return redirect('pre_auth_submit')

        try:
            from employees.models import Company
            from notifications.models import Notification
            from employees.models import Role

            # Always ensure a profile exists for this employee
            company = Company.objects.first()
            profile, _ = EmployeeProfile.objects.get_or_create(
                user=request.user,
                defaults={'company': company, 'department': 'General'},
            )

            form = PreAuthorisationForm.objects.create(
                employee=profile,
                expense_reason=expense_reason,
                estimated_amount=estimated_amount,
            )

            # Notify every admin instantly
            admin_roles = Role.objects.filter(role='admin').select_related('user')
            notified = 0
            for role in admin_roles:
                Notification.objects.create(
                    recipient=role.user,
                    notification_type='admin_alert',
                    subject=f'Pre-Auth Request — Employee {profile.user.username}',
                    body=(
                        f'Employee {profile.user.username} has submitted an Expense '
                        f'Pre-Authorisation request.\n\n'
                        f'Reason: {form.expense_reason}\n'
                        f'Estimated Amount: £{form.estimated_amount}\n\n'
                        f'Please review and approve or reject this request on the Audit Dashboard.'
                    ),
                    delivery_method='dashboard',
                )
                notified += 1

            messages.success(
                request,
                f'Your pre-authorisation request has been submitted to the Finance Auditor '
                f'({notified} auditor{"s" if notified != 1 else ""} notified). '
                f'You will receive a notification once it is reviewed.'
            )
            return redirect('upload_receipt')

        except Exception as e:
            import traceback
            messages.error(request, f'Submission failed: {str(e)}')
            return redirect('pre_auth_submit')

    return render(request, 'pre_auth_form.html')


@login_required
def manage_pre_auth(request, form_id):
    if request.method != 'POST':
        return redirect('audit_dashboard')

    user = request.user
    if not user.roles.filter(role__in=['admin']).exists():
        messages.error(request, "Permission denied.")
        return redirect('home')
        
    form = get_object_or_404(PreAuthorisationForm, id=form_id)
    action = request.POST.get('action')
    
    from notifications.models import Notification

    if action == 'approve':
        form.status = 'approved'
        form.approved_by = user
        form.approved_at = timezone.now()
        form.save()
        messages.success(request, f"Pre-authorisation for {form.employee.user.username} approved.")
        
        Notification.objects.create(
            recipient=form.employee.user,
            notification_type='system_alert',
            subject=f"Claim Reason Approved",
            body=f"Your pre-authorisation request for '{form.expense_reason}' has been approved by Finance.",
            delivery_method='dashboard'
        )

    elif action == 'reject':
        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, "A reason must be provided when rejecting.")
            return redirect('audit_dashboard')

        form.status = 'rejected'
        form.rejection_reason = reason
        form.save()
        messages.error(request, f"Pre-authorisation for {form.employee.user.username} rejected.")
        
        Notification.objects.create(
            recipient=form.employee.user,
            notification_type='system_alert',
            subject=f"Claim Reason Rejected",
            body=f"Your pre-authorisation request for '{form.expense_reason}' was rejected. Reason: {reason}",
            delivery_method='dashboard'
        )

    return redirect('audit_dashboard')
