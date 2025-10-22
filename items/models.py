from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
import os


def item_image_path(instance, filename):
    """Generate upload path for item images."""
    ext = filename.split('.')[-1]
    filename = f"{instance.asset_id}.{ext}"
    return os.path.join('items', filename)


class ItemCategory(models.Model):
    """Category for organizing items (e.g., Electronics, Furniture, etc.)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item Category'
        verbose_name_plural = 'Item Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    """Model representing a tracked item (kuruphun)."""

    class Status(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal (In Use)'
        DAMAGED = 'DAMAGED', 'Damaged'
        LOST = 'LOST', 'Lost'
        REPAIR = 'REPAIR', 'Under Repair'
        PENDING_INSPECTION = 'PENDING_INSPECTION', 'Pending Inspection'
        REMOVED = 'REMOVED', 'Removed from System'

    # Basic Information
    name = models.CharField(max_length=200, verbose_name='Item Name')
    model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Model/Version'
    )
    asset_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Asset ID',
        help_text='Unique asset identification number'
    )

    # Classification
    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.PROTECT,
        related_name='items',
        verbose_name='Category'
    )

    # Details
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description'
    )
    image = models.ImageField(
        upload_to=item_image_path,
        blank=True,
        null=True,
        verbose_name='Item Image'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Purchase Price'
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Location/Room (Deprecated - use home_base_location)'
    )

    # New location fields (database-backed)
    home_base_location = models.ForeignKey(
        'locations.Location',
        on_delete=models.PROTECT,
        related_name='items_home_base',
        blank=True,
        null=True,
        verbose_name='Home Base Location',
        help_text='Default location where item belongs (set by Staff)'
    )
    current_location = models.ForeignKey(
        'locations.Location',
        on_delete=models.PROTECT,
        related_name='items_current',
        blank=True,
        null=True,
        verbose_name='Current Location',
        help_text='Current physical location (updated by item owner)'
    )

    # Room and location description fields (required for new items, nullable for migration)
    room = models.ForeignKey(
        'locations.Room',
        on_delete=models.PROTECT,
        related_name='items',
        blank=True,
        null=True,
        verbose_name='Room',
        help_text='Room code (e.g., sc201, sc202)'
    )
    location_description = models.TextField(
        blank=True,
        default='',
        verbose_name='Location Description',
        help_text='Free-form location description (e.g., "Building 1, floor 2")'
    )

    # Ownership & Status
    current_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='current_items',
        verbose_name='Current Owner'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NORMAL,
        verbose_name='Status'
    )

    # Dates
    date_acquired = models.DateField(
        verbose_name='Date Acquired',
        help_text='Date when item was first added to system'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional metadata
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notes',
        help_text='Internal notes about the item'
    )

    class Meta:
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_id']),
            models.Index(fields=['current_owner', 'status']),
        ]

    def __str__(self):
        return f"{self.asset_id} - {self.name}"

    @property
    def is_active(self):
        """Check if item is in an active state (can be transferred)."""
        return self.status in [
            self.Status.NORMAL,
            self.Status.DAMAGED,
            self.Status.PENDING_INSPECTION
        ]

    @property
    def is_inactive(self):
        """Check if item is inactive (cannot be transferred)."""
        return self.status in [
            self.Status.REPAIR,
            self.Status.LOST,
            self.Status.REMOVED
        ]

    def clean(self):
        """Validate item data."""
        super().clean()

        # Validate that inactive items cannot be transferred
        if self.is_inactive and hasattr(self, '_original_owner'):
            if self._original_owner != self.current_owner:
                raise ValidationError(
                    f"Cannot transfer item with status '{self.get_status_display()}'. "
                    f"Only items with status Normal, Damaged, or Pending Inspection can be transferred."
                )

    def save(self, *args, **kwargs):
        """Override save to track original owner for validation."""
        if self.pk:
            # Store original owner for validation in clean()
            original = Item.objects.get(pk=self.pk)
            self._original_owner = original.current_owner

        self.full_clean()
        super().save(*args, **kwargs)

    def get_transfer_history(self):
        """Get transfer history for this item."""
        return self.transfer_logs.all().order_by('-transferred_at')

    def get_current_transfer_request(self):
        """Get pending transfer request for this item, if any."""
        return self.transfer_requests.filter(status='PENDING').first()

    def has_pending_transfer(self):
        """Check if item has a pending transfer request."""
        return self.transfer_requests.filter(status='PENDING').exists()

