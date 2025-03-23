from django.contrib import admin
from .models import DeliveryOrder

@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ('del_order_id', 'order_status', 'content_id')  # Fields to display
    search_fields = ('del_order_id', 'order_status')  # Searchable fields
