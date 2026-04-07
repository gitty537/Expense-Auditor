from django.conf import settings
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    tax_id = models.CharField(max_length=100, unique=True)
    headquarters_location = models.CharField(max_length=255)
    fiscal_year_start_date = models.DateField()
    max_concurrent_auditors = models.IntegerField(default=5)
    policy_version = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class EmployeeProfile(models.Model):
    DEPARTMENT_CHOICES = [
        ('HR', 'HR'),
        ('Engineering', 'Engineering'),
        ('Finance', 'Finance'),
        ('Sales', 'Sales'),
        ('Operations', 'Operations'),
    ]
    LOCATION_CHOICES = [
        ('New York', 'New York'),
        ('London', 'London'),
        ('Tokyo', 'Tokyo'),
        ('Singapore', 'Singapore'),
        ('Remote', 'Remote'),
    ]
    SENIORITY_CHOICES = [
        ('Junior', 'Junior'),
        ('Mid-Level', 'Mid-Level'),
        ('Senior', 'Senior'),
        ('Lead', 'Lead'),
        ('Manager', 'Manager'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='employees')
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, null=True, blank=True)
    location = models.CharField(max_length=50, choices=LOCATION_CHOICES, null=True, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_employees',
    )
    seniority_level = models.CharField(max_length=50, choices=SENIORITY_CHOICES, null=True, blank=True)
    spending_limit_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class Role(models.Model):
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('admin', 'Admin'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_roles',
    )

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class EmployeeWhitelist(models.Model):
    employee_id = models.CharField(max_length=5, unique=True, help_text="5-digit employee ID")
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ID: {self.employee_id} ({'Used' if self.is_used else 'Available'})"
