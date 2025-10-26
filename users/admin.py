from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""

    list_display = [
        'email', 'full_name', 'role', 'item_count',
        'is_pre_registered', 'is_active', 'created_at'
    ]
    list_filter = ['role', 'is_pre_registered', 'is_active', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'department']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'department')}),
        ('Permissions', {
            'fields': ('role', 'is_auditor', 'is_pre_registered', 'is_active', 'is_staff', 'is_superuser'),
        }),
        ('Preferences', {
            'fields': ('disable_expiration_emails',),
        }),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_pre_registered'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login']

    def full_name(self, obj):
        """Display full name."""
        return obj.get_full_name()
    full_name.short_description = 'Name'

    def item_count(self, obj):
        """Display count of items held by user."""
        count = obj.get_item_count()
        if count > 0:
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>', count)
        return count
    item_count.short_description = 'Items Held'
