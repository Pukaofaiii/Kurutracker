"""
URL configuration for transfers app.
"""

from django.urls import path
from . import views

app_name = 'transfers'

urlpatterns = [
    path('', views.transfer_overview, name='transfer_overview'),
    path('create/', views.create_transfer_request, name='create_transfer'),
    path('return/<int:item_id>/', views.create_return_request, name='create_return'),
    path('pending/', views.pending_requests, name='pending_requests'),
    path('<int:pk>/accept/', views.accept_request, name='accept_request'),
    path('<int:pk>/reject/', views.reject_request, name='reject_request'),
    path('history/', views.transfer_history, name='transfer_history'),
]
