from rest_framework.decorators import api_view
from rest_framework.response import Response
from delivery.models import DeliveryOrder
from delivery.serializers import DeliveryOrderSerializer
from .models import PickingList
from .serializers import PickingListSerializer  # You might need to create this serializer

@api_view(['GET'])
def approved_orders(request):
    # Using 'Approved' as the status value
    approved_orders = DeliveryOrder.objects.filter(order_status='Approved')
    serializer = DeliveryOrderSerializer(approved_orders, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def picking_lists(request):
    # Get all picking lists
    picking_lists = PickingList.objects.all()
    serializer = PickingListSerializer(picking_lists, many=True)
    return Response(serializer.data)