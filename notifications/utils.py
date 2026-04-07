from .models import Notification
from audit.models import AuditDecision
from django.contrib.auth.models import User
from employees.models import Role
import random
import string

def get_employee_display_name(user):
    """
    Get employee full name with ID. If name is not set, assign a random name.
    Returns format: "FirstName LastName (employee_id)" or "RandomName RandomName (employee_id)"
    """
    # Try to get the employee profile to access the user
    try:
        employee_profile = user.employee_profile
    except:
        employee_profile = None
    
    # Extract employee ID from username (assume username is the employee ID)
    employee_id = user.username
    
    # Check if user has first and last name set
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name} ({employee_id})"
    
    # If not, generate random names and save them
    if not user.first_name or not user.last_name:
        first_names = ['Alex', 'Blake', 'Casey', 'Dakota', 'Elliott', 'Finley', 'Grey', 'Harper', 'Indigo', 'Jordan', 
                       'Kyle', 'Logan', 'Morgan', 'Noah', 'Oakley', 'Parker', 'Quinn', 'Riley', 'Sage', 'Taylor',
                       'Unique', 'Vaughn', 'Windsor', 'Xavier', 'Yarrow', 'Zephyr']
        last_names = ['Anderson', 'Bennett', 'Carter', 'Davis', 'Edwards', 'Franklin', 'Garcia', 'Harrison', 'Irving', 'Jackson',
                      'Kennedy', 'Lawrence', 'Martinez', 'Nelson', 'Oliver', 'Parker', 'Quinn', 'Roberts', 'Stewart', 'Thomas',
                      'Underwood', 'Vaughn', 'Washington', 'Xavier', 'Young', 'Zhang']
        
        generated_first = random.choice(first_names)
        generated_last = random.choice(last_names)
        
        user.first_name = generated_first
        user.last_name = generated_last
        user.save()
        
        return f"{generated_first} {generated_last} ({employee_id})"
    
    return f"{user.first_name or ''} {user.last_name or ''} ({employee_id})".strip()


def send_verification_notifications(audit_decision):
    """
    Send dashboard notifications to the employee (submitter) and all administrators.
    """
    receipt = audit_decision.audit_session.receipt_approval.extracted_data.receipt_upload
    submitter = receipt.employee.user
    employee_display_name = get_employee_display_name(submitter)
    
    status_label = audit_decision.final_status
    if audit_decision.final_status == 'approved':
        status_label = 'accepted'

    # 1. Notify the Employee
    Notification.objects.create(
        recipient=submitter,
        audit_decision=audit_decision,
        notification_type='receipt_verification',
        subject=f"Receipt Verification: {status_label.upper()}",
        body=(
            f"Your receipt from {receipt.upload_timestamp.strftime('%Y-%m-%d')} for "
            f"{receipt.reason or 'No reason provided'} has been {status_label}.\n\n"
            f"Explanation: {audit_decision.generated_explanation}"
        ),
        delivery_method='dashboard'
    )
    
    # 1b. Send Email to the Employee
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        if submitter.email:
            send_mail(
                subject=f"Receipt Verification: {audit_decision.final_status.upper()}",
                message=f"Your receipt from {receipt.upload_timestamp.strftime('%Y-%m-%d')} for {receipt.reason or 'No reason provided'} has been {audit_decision.final_status}.\n\nExplanation: {audit_decision.generated_explanation}",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@expenseauditor.com'),
                recipient_list=[submitter.email],
                fail_silently=True,
            )
    except Exception:
        pass
    
    # 2. Notify all Admins
    admin_roles = Role.objects.filter(role='admin').select_related('user')
    for role in admin_roles:
        admin_user = role.user
        Notification.objects.create(
            recipient=admin_user,
            audit_decision=audit_decision,
            notification_type='admin_alert',
            subject=f"Receipt {audit_decision.final_status.upper()} - {employee_display_name}",
            body=(
                f"Employee {employee_display_name} uploaded a receipt that was classified as "
                f"{audit_decision.final_status}.\n\nExplanation: {audit_decision.generated_explanation}"
            ),
            delivery_method='dashboard'
        )


def send_override_notification(audit_decision):
    """
    Send an update to the employee when an auditor manually overrides the AI decision.
    """
    receipt = audit_decision.audit_session.receipt_approval.extracted_data.receipt_upload
    submitter = receipt.employee.user
    auditor = audit_decision.manually_overridden_by
    auditor_display_name = get_employee_display_name(auditor)
    Notification.objects.create(
        recipient=submitter,
        audit_decision=audit_decision,
        notification_type='audit_override',
        subject=f"Receipt Review Updated: {audit_decision.final_status.upper()}",
        body=(
            f"Your receipt from {receipt.upload_timestamp.strftime('%Y-%m-%d')} for "
            f"{receipt.reason or 'No reason provided'} was reviewed by "
            f"{auditor_display_name} and set to {audit_decision.final_status.upper()}.\n\n"
            f"Override note: {audit_decision.override_reason}"
        ),
        delivery_method='dashboard'
    )
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        if submitter.email:
            send_mail(
                subject=f"Receipt Review Updated: {audit_decision.final_status.upper()}",
                message=(
                    f"Your receipt from {receipt.upload_timestamp.strftime('%Y-%m-%d')} for "
                    f"{receipt.reason or 'No reason provided'} was reviewed by "
                    f"{auditor_display_name} and set to {audit_decision.final_status.upper()}.\n\n"
                    f"Override note: {audit_decision.override_reason}"
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@expenseauditor.com'),
                recipient_list=[submitter.email],
                fail_silently=True,
            )
    except Exception:
        pass
