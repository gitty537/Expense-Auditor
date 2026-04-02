from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Policy
from .forms import PolicyForm

@login_required
def policies_view(request):
    """
    Display policy list with search and filter functionality.
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
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')
    
    # Base queryset
    policies = Policy.objects.all()
    
    # Apply search filter
    if query:
        policies = policies.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )
    
    # Apply category filter
    if category:
        policies = policies.filter(category=category)
    
    # Apply status filter
    if status:
        policies = policies.filter(status=status)
    
    # Get unique categories and statuses for filters
    categories = Policy.CATEGORY_CHOICES
    statuses = Policy.STATUS_CHOICES
    
    context = {
        'policies': policies,
        'query': query,
        'category': category,
        'status': status,
        'categories': categories,
        'statuses': statuses,
        'active_page': 'policies',
    }
    
    return render(request, 'policies.html', context)

@login_required
def policy_detail_view(request, policy_id):
    """
    Display detailed information about a specific policy.
    Only accessible to Finance Manager and Finance Auditor.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager and not user.is_finance_auditor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    
    policy = get_object_or_404(Policy, id=policy_id)
    
    context = {
        'policy': policy,
        'active_page': 'policies',
    }
    
    return render(request, 'policy_detail.html', context)

@login_required
def policy_create_view(request):
    """
    Create a new policy.
    Only accessible to Finance Manager.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager:
        messages.error(request, "Only Finance Managers can create policies.")
        return redirect('policies')
    
    if request.method == 'POST':
        form = PolicyForm(request.POST, request.FILES)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.created_by = user
            policy.save()
            messages.success(request, f'Policy "{policy.title}" created successfully!')
            return redirect('policies')
    else:
        form = PolicyForm()
    
    context = {
        'form': form,
        'active_page': 'policies',
        'form_title': 'Create Policy',
    }
    
    return render(request, 'policy_form.html', context)

@login_required
def policy_edit_view(request, policy_id):
    """
    Edit an existing policy.
    Only accessible to Finance Manager.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager:
        messages.error(request, "Only Finance Managers can edit policies.")
        return redirect('policies')
    
    policy = get_object_or_404(Policy, id=policy_id)
    
    if request.method == 'POST':
        form = PolicyForm(request.POST, request.FILES, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, f'Policy "{policy.title}" updated successfully!')
            return redirect('policies')
    else:
        form = PolicyForm(instance=policy)
    
    context = {
        'form': form,
        'active_page': 'policies',
        'form_title': f'Edit Policy "{policy.title}"',
    }
    
    return render(request, 'policy_form.html', context)

@login_required
def policy_delete_view(request, policy_id):
    """
    Delete a policy.
    Only accessible to Finance Manager.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager:
        messages.error(request, "Only Finance Managers can delete policies.")
        return redirect('policies')
    
    policy = get_object_or_404(Policy, id=policy_id)
    
    if request.method == 'POST':
        policy.delete()
        messages.success(request, f'Policy "{policy.title}" deleted successfully!')
        return redirect('policies')
    
    context = {
        'policy': policy,
        'active_page': 'policies',
    }
    
    return render(request, 'policy_confirm_delete.html', context)
