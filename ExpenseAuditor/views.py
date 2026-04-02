from django.shortcuts import render, redirect
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
from receipts.ocr_processor import ReceiptOCRProcessor
from receipts.tasks import process_receipt_ocr


# ── helpers ──────────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_authenticated and user.roles.filter(role='admin').exists()


# ── public / shared views ─────────────────────────────────────────────────────

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


# ── admin-only: register user ─────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin, login_url='/')
def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', '')

        if not username or not password or not role:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')

        new_user = User.objects.create_user(username=username, email=email, password=password)
        Role.objects.create(user=new_user, role=role, assigned_by=request.user)

        company = Company.objects.first()
        if not company:
            company = Company.objects.create(
                name="Default Corp",
                headquarters_location="HQ",
                fiscal_year_start_date="2026-01-01",
                tax_id="000000",
                policy_version="v1",
            )
        EmployeeProfile.objects.get_or_create(
            user=new_user, defaults={'company': company, 'department': 'HR'}
        )

        messages.success(request, f'User "{username}" successfully registered as {role}.')
        return redirect('home')

    return render(request, 'register.html')


# ── upload view (receipt for employees, policy for admins) ────────────────────

@login_required
def upload_receipt(request):
    user = request.user

    if request.method == 'POST':
        upload_type = request.POST.get('upload_type')
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            messages.error(request, 'No file was selected. Please choose a file and try again.')
            return redirect('upload_receipt')

        # ── RECEIPT ──────────────────────────────────────────────────────────
        if upload_type == 'receipt':
            if not user.roles.filter(role='employee').exists():
                messages.error(request, 'Only employees can upload receipts.')
                return redirect('upload_receipt')

            if uploaded_file.size > 5 * 1024 * 1024:
                messages.error(request, 'Receipt file must not exceed 5 MB.')
                return redirect('upload_receipt')

            expense_date = request.POST.get('expense_date') or None
            reason = request.POST.get('reason', '')

            # Ensure employee profile exists
            employee_profile = EmployeeProfile.objects.filter(user=user).first()
            if not employee_profile:
                company = Company.objects.first()
                if not company:
                    company = Company.objects.create(
                        name="Default Corp",
                        headquarters_location="HQ",
                        fiscal_year_start_date="2026-01-01",
                        tax_id="000000",
                        policy_version="v1",
                    )
                employee_profile = EmployeeProfile.objects.create(
                    user=user, company=company, department='General'
                )

            # Save to DB (persists the file via FileField storage)
            ru = ReceiptUpload.objects.create(
                employee=employee_profile,
                original_file=uploaded_file,
                file_size=uploaded_file.size,
                expense_date=expense_date,
                reason=reason,
            )

            # Non-fatal OCR quality check
            try:
                quality = ReceiptOCRProcessor.assess_quality(ru.original_file.path)
                if not quality.get('is_acceptable', True):
                    issues_str = ', '.join(quality.get('issues', []))
                    messages.warning(
                        request,
                        f'Receipt uploaded but may be low quality ({issues_str}). '
                        'Please re-upload a clearer image if possible.'
                    )
                process_receipt_ocr.delay(ru.id)
            except Exception:
                # OCR is optional — don't block the upload
                pass

            messages.success(request, 'Receipt uploaded successfully and is being processed.')

        # ── POLICY ───────────────────────────────────────────────────────────
        elif upload_type == 'policy':
            if not user.roles.filter(role='admin').exists():
                messages.error(request, 'Only administrators can upload company policy documents.')
                return redirect('upload_receipt')

            # Allow up to 100 MB — comfortably covers 100+ page PDFs
            if uploaded_file.size > 100 * 1024 * 1024:
                messages.error(request, 'Policy document is too large (maximum 100 MB).')
                return redirect('upload_receipt')

            version = request.POST.get('version', '').strip()
            effective_date = request.POST.get('effective_date', '').strip()

            if not version:
                version = f'v{timezone.now().strftime("%Y%m%d-%H%M%S")}'
            if not effective_date:
                effective_date = timezone.now().date()

            if PolicyDocument.objects.filter(version=version).exists():
                messages.error(
                    request,
                    f'A policy with version "{version}" already exists. '
                    'Please choose a unique version name.'
                )
                return redirect('upload_receipt')

            PolicyDocument.objects.create(
                version=version,
                pdf_file=uploaded_file,
                uploaded_by=user,
                effective_date=effective_date,
                is_active=True,
            )
            messages.success(request, f'Policy document "{version}" uploaded successfully.')

        else:
            messages.error(request, 'Invalid upload type.')

        return redirect('upload_receipt')

    # GET — pass role flags to template
    is_admin_flag = user.roles.filter(role='admin').exists()
    is_employee_flag = user.roles.filter(role='employee').exists()
    return render(request, 'upload_receipt.html', {
        'is_admin': is_admin_flag,
        'is_employee': is_employee_flag,
    })
