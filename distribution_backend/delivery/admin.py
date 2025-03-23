from django.contrib import admin
from .models import DeliveryOrder, LogisticsApprovalRequest

@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ('del_order_id', 'order_status', 'content_id')  # Fields to display
    search_fields = ('del_order_id', 'order_status')  # Searchable fields

@admin.register(LogisticsApprovalRequest)
class LogisticsApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ('approval_request_id', 'request_date', 'approval_status', 'approval_date', 'approved_by')
    search_fields = ('approval_request_id', 'approval_status', 'approved_by')