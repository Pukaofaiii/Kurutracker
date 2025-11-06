"""
URL configuration for core app (dashboard views).
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('member/', views.member_dashboard, name='member_dashboard'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('account/', views.account_settings, name='account_settings'),
    path('account/edit/', views.edit_profile, name='edit_profile'),
]
