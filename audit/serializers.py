from rest_framework import serializers

from employees.serializers import UserSerializer
from policies.serializers import PolicyDocumentSerializer
from receipts.serializers import ReceiptApprovalSerializer
from .models import AuditDecision, AuditLog, AuditSession


class AuditSessionSerializer(serializers.ModelSerializer):
    receipt_approval = ReceiptApprovalSerializer(read_only=True)
    policy_version_used = PolicyDocumentSerializer(read_only=True)

    class Meta:
        model = AuditSession
        fields = '__all__'


class AuditDecisionSerializer(serializers.ModelSerializer):
    audit_session = AuditSessionSerializer(read_only=True)
    manually_overridden_by = UserSerializer(read_only=True)

    class Meta:
        model = AuditDecision
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    audit_decision = AuditDecisionSerializer(read_only=True)
    actor = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'
