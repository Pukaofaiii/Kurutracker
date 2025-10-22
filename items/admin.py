from django.contrib import admin
from django.utils.html import format_html
from .models import Item, ItemCategory


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    """Admin for Item Categories."""

    list_display = ['name', 'item_count', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

    def item_count(self, obj):
        """Display count of items in category."""
        count = obj.items.count()
        return count
    item_count.short_description = 'Items'


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin for Items."""

    list_display = [
        'asset_id', 'name', 'category', 'current_owner',
        'status_badge', 'price', 'date_acquired'
    ]
    list_filter = ['status', 'category', 'current_owner', 'date_acquired']
    search_fields = ['asset_id', 'name', 'model', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'model', 'asset_id', 'category')
        }),
        ('Details', {
            'fields': ('description', 'image', 'price', 'location')
        }),
        ('Ownership & Status', {
            'fields': ('current_owner', 'status', 'date_acquired')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'NORMAL': 'green',
            'DAMAGED': 'orange',
            'LOST': 'red',
            'REPAIR': 'blue',
            'PENDING_INSPECTION': 'yellow',
            'REMOVED': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
