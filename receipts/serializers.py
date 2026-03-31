from rest_framework import serializers

from employees.serializers import EmployeeProfileSerializer, UserSerializer
from .models import ExtractedReceiptData, ReceiptApproval, ReceiptUpload


class ReceiptUploadSerializer(serializers.ModelSerializer):
    employee = EmployeeProfileSerializer(read_only=True)

    class Meta:
        model = ReceiptUpload
        fields = '__all__'


class ExtractedReceiptDataSerializer(serializers.ModelSerializer):
    receipt_upload = ReceiptUploadSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = ExtractedReceiptData
        fields = '__all__'


class ReceiptApprovalSerializer(serializers.ModelSerializer):
    extracted_data = ExtractedReceiptDataSerializer(read_only=True)
    claimed_by = EmployeeProfileSerializer(read_only=True)

    class Meta:
        model = ReceiptApproval
        fields = '__all__'
