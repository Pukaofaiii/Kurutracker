from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Model for in-app notifications.
    Tracks notification events like new requests, expiring requests, etc.
    """

    class NotificationType(models.TextChoices):
        NEW_REQUEST = 'NEW_REQUEST', 'New Transfer Request'
        REQUEST_ACCEPTED = 'REQUEST_ACCEPTED', 'Request Accepted'
        REQUEST_REJECTED = 'REQUEST_REJECTED', 'Request Rejected'
        REQUEST_EXPIRING_SOON = 'REQUEST_EXPIRING_SOON', 'Request Expiring Soon'
        REQUEST_EXPIRED = 'REQUEST_EXPIRED', 'Request Expired'
        ITEM_DAMAGED = 'ITEM_DAMAGED', 'Item Marked as Damaged'
        ITEM_LOST = 'ITEM_LOST', 'Item Marked as Lost'
        ITEM_FOUND = 'ITEM_FOUND', 'Lost Item Found'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Recipient'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        verbose_name='Type'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Title'
    )
    message = models.TextField(
        verbose_name='Message'
    )
    related_request = models.ForeignKey(
        'transfers.TransferRequest',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications',
        verbose_name='Related Request'
    )
    related_item = models.ForeignKey(
        'items.Item',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications',
        verbose_name='Related Item'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Read'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient.email}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
