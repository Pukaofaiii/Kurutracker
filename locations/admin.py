from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['building', 'floor', 'room', 'is_active', 'created_at']
    list_filter = ['building', 'is_active']
    search_fields = ['building', 'floor', 'room', 'description']
    ordering = ['building', 'floor', 'room']
    list_editable = ['is_active']

    fieldsets = (
        ('Location Information', {
            'fields': ('building', 'floor', 'room', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
