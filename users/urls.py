"""
URL configuration for users app.
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('pre-register/', views.user_pre_register, name='user_pre_register'),
    path('<int:pk>/', views.user_detail, name='user_detail'),
    path('<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('<int:pk>/deactivate/', views.user_deactivate, name='user_deactivate'),
    path('<int:pk>/activate/', views.user_activate, name='user_activate'),
    path('<int:pk>/forced-transfer/', views.user_forced_transfer, name='user_forced_transfer'),
    path('<int:pk>/grant-auditor/', views.grant_auditor_permission, name='grant_auditor'),
    path('<int:pk>/revoke-auditor/', views.revoke_auditor_permission, name='revoke_auditor'),
]
