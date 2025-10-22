"""
Notification URL Configuration.
"""

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:pk>/mark-read/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('api/unread-count/', views.get_unread_count_ajax, name='unread_count_ajax'),
]
