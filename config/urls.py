"""
URL configuration for Kurutracker project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import health_check

urlpatterns = [
    # Health check endpoint (for Docker)
    path('health/', health_check, name='health_check'),

    # Django Admin Panel (for advanced management by MANAGER users)
    path('admin/', admin.site.urls),

    # Authentication (django-allauth)
    path('accounts/', include('allauth.urls')),

    # Core app (dashboards)
    path('', include('core.urls')),

    # Users app (will be created)
    path('users/', include('users.urls')),

    # Items app (will be created)
    path('items/', include('items.urls')),

    # Transfers app (will be created)
    path('transfers/', include('transfers.urls')),

    # Notifications app
    path('notifications/', include('notifications.urls')),

    # Audit app
    path('audit/', include('audit.urls')),

    # Locations app (room management)
    path('locations/', include('locations.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
