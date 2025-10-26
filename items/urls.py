"""
URL configuration for items app.
"""

from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'items'

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('create/', views.item_create, name='item_create'),
    path('<int:pk>/', RedirectView.as_view(pattern_name='items:item_update', permanent=True), name='item_detail'),
    path('<int:pk>/update/', views.item_update, name='item_update'),
    path('<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('<int:pk>/update-location/', views.update_item_location, name='update_location'),

    # Bulk Operations
    path('bulk/delete/', views.bulk_delete_items, name='bulk_delete'),
    path('bulk/status/', views.bulk_update_status, name='bulk_status'),
    path('bulk/transfer/', views.bulk_transfer_items, name='bulk_transfer'),
    path('bulk/restore/', views.bulk_restore_items, name='bulk_restore'),

    # Removed Items Management
    path('removed/', views.removed_items_list, name='removed_items_list'),
    path('<int:pk>/restore/', views.restore_item, name='restore_item'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
]
