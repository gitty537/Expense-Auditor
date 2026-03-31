from rest_framework import serializers

from audit.serializers import AuditDecisionSerializer
from employees.serializers import UserSerializer
from .models import Notification, NotificationTemplate


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(read_only=True)
    audit_decision = AuditDecisionSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
