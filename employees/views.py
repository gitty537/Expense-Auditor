from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Employee
from .forms import EmployeeForm

@login_required
def employees_view(request):
    """
    Display employee list with search and filter functionality.
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
    department = request.GET.get('department', '')
    status = request.GET.get('status', '')
    
    # Base queryset
    employees = Employee.objects.all().select_related('user')
    
    # Apply search filter
    if query:
        employees = employees.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(employee_id__icontains=query)
        )
    
    # Apply department filter
    if department:
        employees = employees.filter(department=department)
    
    # Apply status filter
    if status:
        employees = employees.filter(status=status)
    
    # Get unique departments and statuses for filters
    departments = Employee.DEPARTMENT_CHOICES
    statuses = Employee.STATUS_CHOICES
    
    context = {
        'employees': employees,
        'query': query,
        'department': department,
        'status': status,
        'departments': departments,
        'statuses': statuses,
        'active_page': 'employees',
    }
    
    return render(request, 'employees.html', context)

@login_required
def employee_detail_view(request, employee_id):
    """
    Display detailed information about a specific employee.
    Only accessible to Finance Manager and Finance Auditor.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager and not user.is_finance_auditor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    
    employee = get_object_or_404(Employee.objects.select_related('user'), id=employee_id)
    
    context = {
        'employee': employee,
        'active_page': 'employees',
    }
    
    return render(request, 'employee_detail.html', context)

@login_required
def employee_create_view(request):
    """
    Create a new employee.
    Only accessible to Finance Manager.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager:
        messages.error(request, "Only Finance Managers can create employees.")
        return redirect('employees')
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.created_by = user
            employee.save()
            messages.success(request, f'Employee {employee.employee_id} created successfully!')
            return redirect('employees')
    else:
        form = EmployeeForm()
    
    context = {
        'form': form,
        'active_page': 'employees',
        'form_title': 'Create Employee',
    }
    
    return render(request, 'employee_form.html', context)

@login_required
def employee_edit_view(request, employee_id):
    """
    Edit an existing employee.
    Only accessible to Finance Manager.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager:
        messages.error(request, "Only Finance Managers can edit employees.")
        return redirect('employees')
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f'Employee {employee.employee_id} updated successfully!')
            return redirect('employees')
    else:
        form = EmployeeForm(instance=employee)
    
    context = {
        'form': form,
        'active_page': 'employees',
        'form_title': f'Edit Employee {employee.employee_id}',
    }
    
    return render(request, 'employee_form.html', context)

@login_required
def employee_delete_view(request, employee_id):
    """
    Delete an employee.
    Only accessible to Finance Manager.
    """
    user = request.user
    
    # Authorization check
    if not user.is_finance_manager:
        messages.error(request, "Only Finance Managers can delete employees.")
        return redirect('employees')
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        employee.delete()
        messages.success(request, f'Employee {employee.employee_id} deleted successfully!')
        return redirect('employees')
    
    context = {
        'employee': employee,
        'active_page': 'employees',
    }
    
    return render(request, 'employee_confirm_delete.html', context)
