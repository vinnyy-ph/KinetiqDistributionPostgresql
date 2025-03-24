from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import DeliveryOrder
from .serializers import DeliveryOrderSerializer

# ViewSet for DeliveryOrder
class DeliveryOrderViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOrder.objects.all()
    serializer_class = DeliveryOrderSerializer

# API endpoint to get external deliveries
@api_view(['GET'])
def external_deliveries(request):
    external_orders = DeliveryOrder.objects.filter(del_type='External Delivery')
    serializer = DeliveryOrderSerializer(external_orders, many=True)
    return Response(serializer.data)


# API endpoint to get internal deliveries
@api_view(['GET'])
def internal_deliveries(request):
    internal_orders = DeliveryOrder.objects.filter(del_type='Internal Delivery')
    serializer = DeliveryOrderSerializer(internal_orders, many=True)
    return Response(serializer.data)