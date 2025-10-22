"""
Location URL Configuration.
"""

from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    # Room management (manager only)
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/create/', views.room_create, name='room_create'),
    path('rooms/<int:pk>/edit/', views.room_edit, name='room_edit'),
    path('rooms/<int:pk>/delete/', views.room_delete, name='room_delete'),
    path('rooms/<int:pk>/activate/', views.room_activate, name='room_activate'),
]
