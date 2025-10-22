from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__email', 'title', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'notification_type', 'title', 'message')
        }),
        ('Related Objects', {
            'fields': ('related_request', 'related_item')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    )
