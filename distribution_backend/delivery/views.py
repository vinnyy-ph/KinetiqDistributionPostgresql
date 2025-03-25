from django.shortcuts import render
from .models import DeliveryOrder

def delivery_order_list(request):
    delivery_orders = DeliveryOrder.objects.all()
    return render(request, 'delivery_orders.html', {'delivery_orders': delivery_orders})