from django.db import models


class Room(models.Model):
    """
    Model for room codes (e.g., sc201, sc202, etc.).
    Used for quick room selection with autocomplete.
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Room Code',
        help_text='Room identifier (e.g., sc201, sc202)'
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Description',
        help_text='Optional room description'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active',
        help_text='Inactive rooms are hidden from selection'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.code


class Location(models.Model):
    """
    Model for tracking physical locations of items.
    Supports building → floor → room hierarchy.
    """

    building = models.CharField(
        max_length=100,
        verbose_name='Building',
        help_text='Building name or number'
    )
    floor = models.CharField(
        max_length=50,
        verbose_name='Floor',
        help_text='Floor number or name'
    )
    room = models.CharField(
        max_length=50,
        verbose_name='Room',
        help_text='Room number (e.g., 201-254)'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description',
        help_text='Additional location details'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active',
        help_text='Inactive locations are hidden from selection'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['building', 'floor', 'room']
        unique_together = ['building', 'floor', 'room']
        indexes = [
            models.Index(fields=['building', 'floor']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.building} - Floor {self.floor} - Room {self.room}"

    @property
    def full_address(self):
        """Return full location address."""
        return f"{self.building}, Floor {self.floor}, Room {self.room}"
