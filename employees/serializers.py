from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Company, EmployeeProfile, Role


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
        ]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class EmployeeProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    company = CompanySerializer(read_only=True)
    manager = UserSerializer(read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    assigned_by = UserSerializer(read_only=True)

    class Meta:
        model = Role
        fields = '__all__'
