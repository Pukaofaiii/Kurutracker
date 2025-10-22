from django.contrib import admin
from django.utils.html import format_html
from .models import TransferRequest, TransferLog


@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    """Admin for Transfer Requests."""

    list_display = [
        'item', 'request_type', 'from_user', 'to_user',
        'status_badge', 'created_at', 'resolved_at'
    ]
    list_filter = ['status', 'request_type', 'created_at']
    search_fields = ['item__asset_id', 'from_user__email', 'to_user__email', 'notes']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']

    fieldsets = (
        ('Request Info', {
            'fields': ('request_type', 'status', 'item')
        }),
        ('Parties', {
            'fields': ('from_user', 'to_user')
        }),
        ('Details', {
            'fields': ('notes', 'new_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'PENDING': 'orange',
            'ACCEPTED': 'green',
            'REJECTED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(TransferLog)
class TransferLogAdmin(admin.ModelAdmin):
    """Admin for Transfer Logs (read-only audit trail)."""

    list_display = [
        'item', 'from_user', 'to_user',
        'transferred_at', 'is_forced'
    ]
    list_filter = ['is_forced', 'transferred_at']
    search_fields = ['item__asset_id', 'from_user__email', 'to_user__email', 'notes']
    ordering = ['-transferred_at']
    readonly_fields = [
        'item', 'from_user', 'to_user', 'request',
        'transferred_at', 'notes', 'is_forced'
    ]

    def has_add_permission(self, request):
        """Transfer logs are created automatically, not manually."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Transfer logs are immutable audit trail."""
        return False

    def has_change_permission(self, request, obj=None):
        """Transfer logs cannot be modified."""
        return False
