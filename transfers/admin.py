from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from .models import TransferRequest, TransferLog


@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    """Admin for Transfer Requests with expiration management."""

    list_display = [
        'item', 'request_type', 'from_user', 'to_user',
        'status_badge', 'expiration_countdown', 'created_at', 'resolved_at'
    ]
    list_filter = [
        'status', 'request_type', 'created_at',
        'warning_48h_sent', 'warning_24h_sent'
    ]
    search_fields = ['item__asset_id', 'from_user__email', 'to_user__email', 'notes']
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'resolved_at', 'original_item_status',
        'warning_48h_sent', 'warning_24h_sent', 'manually_expired_by'
    ]
    actions = [
        'extend_expiration_3_days',
        'extend_expiration_7_days',
        'manually_expire_requests'
    ]

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
        ('Expiration Tracking', {
            'fields': (
                'expires_at', 'expiration_extended_until',
                'warning_48h_sent', 'warning_24h_sent',
                'manually_expired_by', 'original_item_status'
            ),
            'classes': ('collapse',)
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
            'EXPIRED': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def expiration_countdown(self, obj):
        """Display time until expiration with urgency indicator."""
        if obj.status != TransferRequest.Status.PENDING:
            return '-'

        time_delta = obj.time_until_expiration()
        if not time_delta:
            return format_html(
                '<span style="color: red; font-weight: bold;">EXPIRED</span>'
            )

        hours = time_delta.total_seconds() / 3600
        days = time_delta.days

        if hours < 24:
            # Critical: less than 24 hours
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ {} hours</span>',
                int(hours)
            )
        elif hours < 48:
            # Warning: less than 48 hours
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠️ {} hours</span>',
                int(hours)
            )
        else:
            # Normal: more than 48 hours
            return format_html(
                '<span style="color: green;">{} days</span>',
                days
            )
    expiration_countdown.short_description = 'Expires In'

    def extend_expiration_3_days(self, request, queryset):
        """Extend expiration deadline by 3 days for selected requests."""
        if not request.user.is_manager and not request.user.is_superuser:
            self.message_user(
                request,
                "Only managers can extend expiration deadlines.",
                level=messages.ERROR
            )
            return

        pending_requests = queryset.filter(status=TransferRequest.Status.PENDING)
        count = 0

        for req in pending_requests:
            try:
                req.extend_expiration(days=3, extended_by_user=request.user)
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error extending request {req.pk}: {str(e)}",
                    level=messages.ERROR
                )

        self.message_user(
            request,
            f"Successfully extended {count} request(s) by 3 days.",
            level=messages.SUCCESS
        )
    extend_expiration_3_days.short_description = "Extend expiration by 3 days"

    def extend_expiration_7_days(self, request, queryset):
        """Extend expiration deadline by 7 days for selected requests."""
        if not request.user.is_manager and not request.user.is_superuser:
            self.message_user(
                request,
                "Only managers can extend expiration deadlines.",
                level=messages.ERROR
            )
            return

        pending_requests = queryset.filter(status=TransferRequest.Status.PENDING)
        count = 0

        for req in pending_requests:
            try:
                req.extend_expiration(days=7, extended_by_user=request.user)
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error extending request {req.pk}: {str(e)}",
                    level=messages.ERROR
                )

        self.message_user(
            request,
            f"Successfully extended {count} request(s) by 7 days.",
            level=messages.SUCCESS
        )
    extend_expiration_7_days.short_description = "Extend expiration by 7 days"

    def manually_expire_requests(self, request, queryset):
        """Manually expire selected pending requests."""
        if not request.user.is_manager and not request.user.is_superuser:
            self.message_user(
                request,
                "Only managers can manually expire requests.",
                level=messages.ERROR
            )
            return

        from notifications.utils import notify_request_expired

        pending_requests = queryset.filter(status=TransferRequest.Status.PENDING)
        count = 0

        for req in pending_requests:
            try:
                req.expire(expired_by_user=request.user)
                notify_request_expired(req)
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error expiring request {req.pk}: {str(e)}",
                    level=messages.ERROR
                )

        self.message_user(
            request,
            f"Successfully manually expired {count} request(s).",
            level=messages.SUCCESS
        )
    manually_expire_requests.short_description = "Manually expire selected requests"


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
