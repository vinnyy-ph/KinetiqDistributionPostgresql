from rest_framework import serializers
from .models import DeliveryOrder, LogisticsApprovalRequest

class LogisticsApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticsApprovalRequest
        fields = '__all__'

class DeliveryOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOrder
        fields = '__all__'