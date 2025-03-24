from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'delivery-orders', views.DeliveryOrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('external-deliveries/', views.external_deliveries, name='external-deliveries'),
    path('internal-deliveries/', views.internal_deliveries, name='internal-deliveries'),
]