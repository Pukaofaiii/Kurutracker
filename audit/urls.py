"""
URL configuration for audit app.
"""

from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_checklist, name='audit_checklist'),
    path('report/', views.audit_report, name='audit_report'),
    path('update-status/<int:pk>/', views.update_item_status, name='update_item_status'),
    path('lost-items/', views.audit_lost_items, name='audit_lost_items'),
    path('mark-damaged/<int:item_id>/', views.audit_mark_damaged, name='mark_damaged'),
    path('mark-lost/<int:item_id>/', views.audit_mark_lost, name='mark_lost'),
    path('found-item/<int:item_id>/', views.audit_found_item, name='found_item'),
]
