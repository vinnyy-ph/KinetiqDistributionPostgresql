from django.contrib import admin
from django.urls import path, include  # Add include import

urlpatterns = [
    path('admin/', admin.site.urls),  # Remove duplicate
    path('api/delivery/', include('delivery.urls')),
    path('api/picking/', include('picking.urls')),
]