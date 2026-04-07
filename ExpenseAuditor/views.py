from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.files.storage import default_storage
from django.utils import timezone
from django.contrib.auth.models import User

from employees.models import Company, EmployeeProfile, Role
from receipts.models import ReceiptUpload
from policies.models import PolicyDocument, PolicyRule
from audit.models import AuditDecision
from notifications.models import Notification
from notifications.utils import send_verification_notifications, send_override_notification

from receipts.ocr_processor import ReceiptOCRProcessor
from receipts.tasks import process_receipt_ocr


# ── helpers ──────────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_authenticated and user.roles.filter(role='admin').exists()


# ── public / shared views ─────────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        if request.user.roles.filter(role='admin').exists():
            return redirect('audit_dashboard')
        if request.user.roles.filter(role='employee').exists():
            return redirect('upload_receipt')
    else:
        return redirect('login')
        
    context = {
        'company_count': Company.objects.count(),
        'employee_count': EmployeeProfile.objects.count(),
        'recent_receipts': ReceiptUpload.objects.order_by('-upload_timestamp')[:5],
        'active_policies': PolicyDocument.objects.filter(is_active=True).order_by('-effective_date')[:5],
        'recent_decisions': AuditDecision.objects.order_by('-created_at')[:5],
    }
    return render(request, 'home.html', context)





def policy_list(request):
    policies = PolicyDocument.objects.order_by('-effective_date')[:25]
    rules = PolicyRule.objects.order_by('-created_at')[:25]
    return render(request, 'policies.html', {'policies': policies, 'rules': rules})


@login_required
def audit_dashboard(request):
    from django.db.models import Case, When, Value, IntegerField
    user = request.user
    is_admin_flag = is_admin(user)
    
    from audit.models import PreAuthorisationForm
    
    if is_admin_flag:
        decisions = AuditDecision.objects.filter(manually_overridden_at__isnull=True).select_related(
            'audit_session__receipt_approval__extracted_data__receipt_upload'
        ).annotate(
            risk_rank=Case(
                When(final_status='flagged', then=Value(1)),
                When(final_status='rejected', then=Value(2)),
                When(final_status='approved', then=Value(3)),
                output_field=IntegerField(),
            )
        ).order_by('risk_rank', 'approval_confidence_score', '-created_at')[:25]
        pending_forms = PreAuthorisationForm.objects.filter(status='pending').order_by('-created_at')
    else:
        decisions = AuditDecision.objects.filter(
            audit_session__receipt_approval__claimed_by__user=user
        ).select_related(
            'audit_session__receipt_approval__extracted_data__receipt_upload'
        ).order_by('-created_at')[:25]
        pending_forms = None
        
    return render(request, 'audit.html', {'decisions': decisions, 'is_admin': is_admin_flag, 'pending_forms': pending_forms})



@login_required
@user_passes_test(is_admin, login_url='/')
def audit_detail(request, decision_id):
    from django.shortcuts import get_object_or_404
    decision = get_object_or_404(AuditDecision.objects.select_related(
        'audit_session__receipt_approval__extracted_data__receipt_upload'
    ), id=decision_id)
    
    if request.method == 'POST':
        override_status = request.POST.get('override_status')
        override_reason = request.POST.get('override_reason')
        if override_status in ['approved', 'rejected', 'flagged'] and override_reason:
            decision.final_status = override_status
            decision.decision_made_by_system = False
            decision.manually_overridden_at = timezone.now()
            decision.manually_overridden_by = request.user
            decision.override_reason = override_reason
            decision.save()
            send_override_notification(decision)
            messages.success(request, f'Decision permanently overridden to {override_status.upper()}.')
            return redirect('audit_detail', decision_id=decision_id)
            
    return render(request, 'audit_detail.html', {'decision': decision})


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:50]
    # Mark all unread as read now that the user is viewing them
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())
    return render(request, 'notifications.html', {'notifications': notifications})


# ── admin-only: register user ─────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin, login_url='/')
def register_admin(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id', '').strip()
        password = request.POST.get('password', '')
        
        if not employee_id or not password:
            messages.error(request, 'Please provide both username and password.')
            return redirect('register_admin')

        if User.objects.filter(username=employee_id).exists():
            messages.error(request, 'User with this ID already exists.')
            return redirect('register_admin')
            
        new_user = User.objects.create_user(username=employee_id, password=password)
        company = Company.objects.first()
        if not company:
            company = Company.objects.create(name="Default Corp", headquarters_location="HQ", policy_version="v1")
        
        EmployeeProfile.objects.create(user=new_user, company=company, department='Finance Audit')
        Role.objects.create(user=new_user, role='admin', assigned_by=request.user)
        
        messages.success(request, f'Finance Auditor {employee_id} successfully provisioned.')
        return redirect('audit_dashboard')
        
    return render(request, 'register_admin.html')


# ── upload view (receipt for employees, policy for admins) ────────────────────

@login_required
def upload_receipt(request):
    user = request.user

    if request.method == 'POST':
        upload_type = request.POST.get('upload_type')
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            uploaded_file = request.FILES.get('receipt_file') or request.FILES.get('policy_file')

        if not uploaded_file:
            messages.error(request, 'No file was selected. Please choose a file and try again.')
            return redirect('upload_receipt')

        if upload_type == 'receipt' or request.POST.get('form_type') == 'receipt':
            if not user.roles.filter(role='employee').exists() or user.roles.filter(role='admin').exists():
                messages.error(request, 'Only employees can upload receipts.')
                return redirect('upload_receipt')

            if uploaded_file.size > 5 * 1024 * 1024:
                messages.error(request, 'Receipt file must not exceed 5 MB.')
                return redirect('upload_receipt')

            expense_date = request.POST.get('expense_date') or None
            reason = request.POST.get('reason', '')

            employee_profile, _ = EmployeeProfile.objects.get_or_create(
                user=user, defaults={'company': Company.objects.first(), 'department': 'General'}
            )

            ru = ReceiptUpload.objects.create(
                employee=employee_profile,
                original_file=uploaded_file,
                file_size=uploaded_file.size,
                expense_date=expense_date,
                reason=reason,
            )

            # Strict image quality control
            quality = ReceiptOCRProcessor.assess_quality(ru.original_file.path)
            if not quality.get('is_acceptable', True):
                issues_str = ', '.join(quality.get('issues', []))
                ru.original_file.delete()
                ru.delete()
                messages.error(
                    request,
                    f'Upload rejected. The image is too poor quality ({issues_str}). '
                    'Please capture a sharper, well-lit photo and try again.'
                )
                return redirect('upload_receipt')

            process_receipt_ocr(ru.id)
            messages.success(request, 'Receipt uploaded successfully and is being processed.')
            return redirect('upload_receipt')

        elif upload_type == 'policy' or request.POST.get('form_type') == 'policy':
            if not user.roles.filter(role='admin').exists():
                messages.error(request, 'Only administrators can upload policy documents.')
                return redirect('upload_receipt')

            if uploaded_file.size > 100 * 1024 * 1024:
                messages.error(request, 'Policy document is too large.')
                return redirect('upload_receipt')

            version = request.POST.get('version', '').strip()
            effective_date = request.POST.get('effective_date') or timezone.now().date()
            if not version: version = f'v{timezone.now().strftime("%Y%m%d%H%M%S")}'

            PolicyDocument.objects.create(
                version=version, pdf_file=uploaded_file, uploaded_by=user,
                effective_date=effective_date, is_active=True,
            )
            messages.success(request, f'Policy "{version}" uploaded.')
            return redirect('upload_receipt')

    is_admin_flag = user.roles.filter(role='admin').exists()
    is_employee_flag = user.roles.filter(role='employee').exists()
    my_claims = ReceiptUpload.objects.filter(employee__user=user).order_by('-upload_timestamp') if is_employee_flag else []
    
    return render(request, 'upload_receipt.html', {
        'is_admin': is_admin_flag,
        'is_employee': is_employee_flag,
        'my_claims': my_claims
    })


@login_required
@user_passes_test(is_admin)
def approve_policy(request, policy_id):
    """
    Handles multi-admin consensus. Once all required admins approve, activate.
    """
    from policies.models import PolicyApproval
    policy = get_object_or_404(PolicyDocument, id=policy_id)
    if policy.status != 'pending':
        messages.error(request, 'This policy is not pending review.')
        return redirect('policy_list')

    if policy.uploaded_by == request.user:
        messages.error(request, 'You cannot approve a policy you uploaded.')
        return redirect('policy_list')

    PolicyApproval.objects.get_or_create(policy=policy, admin=request.user)

    all_other_admins_count = User.objects.filter(roles__role='admin').exclude(id=policy.uploaded_by_id).count()
    current_approvals_count = policy.approvals.count()

    if current_approvals_count >= all_other_admins_count:
        policy.status = 'active'
        policy.is_active = True
        policy.save()
        messages.success(request, f'Policy {policy.version} is now ACTIVE.')
    else:
        messages.success(request, f'Approved policy. {all_other_admins_count - current_approvals_count} more needed.')

    return redirect('policy_list')


def register_employee(request):
    from employees.models import EmployeeWhitelist
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not employee_id or not password or not confirm_password:
            messages.error(request, 'Please provide employee ID and enter password twice.')
            return redirect('register_employee')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('register_employee')

        if len(employee_id) != 5 or not employee_id.isdigit():
            messages.error(request, 'Employee ID must be exactly 5 digits.')
            return redirect('register_employee')

        # check whitelist natively:
        whitelist_entry = EmployeeWhitelist.objects.filter(employee_id=employee_id, is_used=False).first()
        if not whitelist_entry:
            messages.error(request, 'ID not found in whitelist or already used.')
            return redirect('register_employee')

        if User.objects.filter(username=employee_id).exists():
            messages.error(request, 'User with this ID already exists.')
            return redirect('register_employee')

        new_user = User.objects.create_user(username=employee_id, password=password)

        company = Company.objects.first()
        if not company:
            company = Company.objects.create(name="Default Corp", headquarters_location="HQ", fiscal_year_start_date="2026-01-01", tax_id="000000", policy_version="v1")

        EmployeeProfile.objects.create(user=new_user, company=company, department='General')
        Role.objects.create(user=new_user, role='employee')
        
        whitelist_entry.is_used = True
        whitelist_entry.save()

        messages.success(request, f'Employee {employee_id} successfully provisioned.')
        return redirect('home')

    # Drain any stale messages from other pages so they don't leak onto this page
    storage = messages.get_messages(request)
    for _ in storage:
        pass  # iterating marks them as consumed
    storage.used = True

    return render(request, 'register.html')
