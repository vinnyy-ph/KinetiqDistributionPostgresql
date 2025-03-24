from rest_framework import serializers
from .models import PickingList
from delivery.serializers import DeliveryOrderSerializer

class PickingListSerializer(serializers.ModelSerializer):
    approval_request_details = serializers.SerializerMethodField()
    
    class Meta:
        model = PickingList
        fields = '__all__'
    
    def get_approval_request_details(self, obj):
        if obj.approval_request:
            from delivery.serializers import LogisticsApprovalRequestSerializer
            return LogisticsApprovalRequestSerializer(obj.approval_request).data
        return None