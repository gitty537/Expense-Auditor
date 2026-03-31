from rest_framework import serializers

from employees.serializers import UserSerializer
from .models import PolicyDocument, PolicyIndex, PolicyRule


class PolicyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = PolicyDocument
        fields = '__all__'


class PolicyRuleSerializer(serializers.ModelSerializer):
    policy_version = PolicyDocumentSerializer(read_only=True)

    class Meta:
        model = PolicyRule
        fields = '__all__'


class PolicyIndexSerializer(serializers.ModelSerializer):
    policy_rule = PolicyRuleSerializer(read_only=True)

    class Meta:
        model = PolicyIndex
        fields = '__all__'
