from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Register your viewsets here if needed

urlpatterns = [
    path('', include(router.urls)),
    path('approved-orders/', views.approved_orders, name='approved-orders'),
    path('picking-lists/', views.picking_lists, name='picking-lists'),
]