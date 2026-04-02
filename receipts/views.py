from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Receipt
from .forms import ReceiptForm

@login_required
def receipts_view(request):
    """
    Display receipt list with search and filter functionality.
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
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    receipts = Receipt.objects.all().select_related('employee', 'approved_by')
    
    # Apply search filter
    if query:
        receipts = receipts.filter(
            Q(employee__user__first_name__icontains=query) |
            Q(employee__user__last_name__icontains=query) |
            Q(employee__user__email__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )
    
    # Apply status filter
    if status:
        receipts = receipts.filter(status=status)
    
    # Apply date filters
    if date_from:
        receipts = receipts.filter(date__gte=date_from)
    if date_to:
        receipts = receipts.filter(date__lte=date_to)
    
    # Get unique statuses for filters
    statuses = Receipt.STATUS_CHOICES
    
    context = {
        'receipts': receipts,
        'query': query,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'statuses': statuses,
        'active_page': 'receipts',
    }
    
    return render(request, 'receipts.html', context)

@login_required
def receipt_detail_view(request, receipt_id):
    """
    Display detailed information about a specific receipt.
    Only accessible to Finance Manager and Finance Auditor.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager and not user.is_finance_auditor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    
    receipt = get_object_or_404(Receipt.objects.select_related('employee', 'approved_by'), id=receipt_id)
    
    context = {
        'receipt': receipt,
        'active_page': 'receipts',
    }
    
    return render(request, 'receipt_detail.html', context)

@login_required
def receipt_create_view(request):
    """
    Create a new receipt.
    Only accessible to Employees.
    """
    user = request.user
    
    # Authorization check
    if not user.is_employee:
        messages.error(request, "Only employees can create receipts.")
        return redirect('receipts')
    
    if request.method == 'POST':
        form = ReceiptForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.employee = user.employee
            receipt.status = Receipt.STATUS_PENDING
            receipt.save()
            messages.success(request, f'Receipt for "{receipt.description}" submitted successfully!')
            return redirect('receipts')
    else:
        form = ReceiptForm()
    
    context = {
        'form': form,
        'active_page': 'receipts',
        'form_title': 'Submit New Receipt',
    }
    
    return render(request, 'receipt_form.html', context)

@login_required
def receipt_edit_view(request, receipt_id):
    """
    Edit a receipt.
    Only accessible to the employee who created it (if pending).
    """
    user = request.user
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    # Authorization check
    if receipt.employee.user != user:
        messages.error(request, "You can only edit your own receipts.")
        return redirect('receipts')
    
    if receipt.status != Receipt.STATUS_PENDING:
        messages.error(request, "You can only edit pending receipts.")
        return redirect('receipts')
    
    if request.method == 'POST':
        form = ReceiptForm(request.POST, request.FILES, instance=receipt)
        if form.is_valid():
            form.save()
            messages.success(request, f'Receipt "{receipt.description}" updated successfully!')
            return redirect('receipts')
    else:
        form = ReceiptForm(instance=receipt)
    
    context = {
        'form': form,
        'active_page': 'receipts',
        'form_title': f'Edit Receipt "{receipt.description}"',
    }
    
    return render(request, 'receipt_form.html', context)

@login_required
def receipt_delete_view(request, receipt_id):
    """
    Delete a receipt.
    Only accessible to the employee who created it (if pending).
    """
    user = request.user
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    # Authorization check
    if receipt.employee.user != user:
        messages.error(request, "You can only delete your own receipts.")
        return redirect('receipts')
    
    if receipt.status != Receipt.STATUS_PENDING:
        messages.error(request, "You can only delete pending receipts.")
        return redirect('receipts')
    
    if request.method == 'POST':
        receipt.delete()
        messages.success(request, f'Receipt "{receipt.description}" deleted successfully!')
        return redirect('receipts')
    
    context = {
        'receipt': receipt,
        'active_page': 'receipts',
    }
    
    return render(request, 'receipt_confirm_delete.html', context)

@login_required
def receipt_approve_view(request, receipt_id):
    """
    Approve or reject a receipt.
    Only accessible to Finance Manager and Finance Auditor.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager and not user.is_finance_auditor:
        messages.error(request, "You do not have permission to approve receipts.")
        return redirect('receipts')
    
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            receipt.status = Receipt.STATUS_APPROVED
            receipt.approved_by = user
            receipt.approved_at = timezone.now()
            receipt.save()
            messages.success(request, f'Receipt "{receipt.description}" approved successfully!')
        elif action == 'reject':
            receipt.status = Receipt.STATUS_REJECTED
            receipt.approved_by = user
            receipt.approved_at = timezone.now()
            receipt.save()
            messages.warning(request, f'Receipt "{receipt.description}" rejected.')
        
        return redirect('receipts')
    
    return redirect('receipts')
