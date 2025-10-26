from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction


class TransferRequest(models.Model):
    """
    Model for transfer requests (Request/Accept workflow).
    Handles both assignment (Staff -> Teacher) and returns (Teacher -> Staff).
    """

    class RequestType(models.TextChoices):
        ASSIGN = 'ASSIGN', 'Assign to User'
        RETURN = 'RETURN', 'Return to Staff'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        EXPIRED = 'EXPIRED', 'Expired'

    # Request metadata
    request_type = models.CharField(
        max_length=10,
        choices=RequestType.choices,
        verbose_name='Request Type'
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Status'
    )

    # Parties involved
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transfer_requests_sent',
        verbose_name='From User'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transfer_requests_received',
        verbose_name='To User'
    )

    # Item being transferred
    item = models.ForeignKey(
        'items.Item',
        on_delete=models.PROTECT,  # Prevent item deletion if transfer requests exist
        related_name='transfer_requests',
        verbose_name='Item'
    )

    # Additional info
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notes',
        help_text='Reason for transfer or condition notes (for returns)'
    )

    # Status update info
    new_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='New Item Status',
        help_text='For returns: Status to set when accepted (e.g., NORMAL, DAMAGED, REPAIR)'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Resolved At',
        help_text='When request was accepted/rejected'
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Expires At',
        help_text='Request expires 7 days after creation'
    )

    # Expiration tracking fields
    original_item_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Original Item Status',
        help_text='Item status before PENDING_INSPECTION (for RETURN requests)'
    )
    expiration_extended_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Extended Until',
        help_text='Admin-extended expiration deadline'
    )
    manually_expired_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='manually_expired_requests',
        verbose_name='Manually Expired By',
        help_text='Manager who manually expired this request'
    )
    warning_48h_sent = models.BooleanField(
        default=False,
        verbose_name='48-Hour Warning Sent',
        help_text='Whether 48-hour expiration warning has been sent'
    )
    warning_24h_sent = models.BooleanField(
        default=False,
        verbose_name='24-Hour Warning Sent',
        help_text='Whether 24-hour expiration warning has been sent'
    )

    class Meta:
        verbose_name = 'Transfer Request'
        verbose_name_plural = 'Transfer Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'to_user']),
            models.Index(fields=['item', 'status']),
            models.Index(fields=['expires_at']),  # For expiration batch jobs
            models.Index(fields=['from_user']),  # For user permission checks
            models.Index(fields=['status', 'expires_at']),  # For expiration queries
            models.Index(fields=['status', 'warning_48h_sent']),  # For warning queries
            models.Index(fields=['status', 'warning_24h_sent']),  # For warning queries
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['item'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_request_per_item'
            )
        ]

    def __str__(self):
        return f"{self.get_request_type_display()}: {self.item.asset_id} from {self.from_user.email} to {self.to_user.email}"

    def save(self, *args, **kwargs):
        """
        Set expires_at to 7 days from creation if not set.
        For RETURN requests, capture original item status before PENDING_INSPECTION.
        """
        if not self.pk:
            # Set expiration date if not already set
            if not self.expires_at:
                from django.utils import timezone
                from datetime import timedelta
                self.expires_at = timezone.now() + timedelta(days=7)

            # For RETURN requests, capture original item status
            if self.request_type == self.RequestType.RETURN and self.item:
                # Store the status before it might be changed to PENDING_INSPECTION
                if not self.original_item_status:
                    self.original_item_status = self.item.status

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if request has expired."""
        from django.utils import timezone
        if self.status == self.Status.PENDING and self.expires_at:
            return timezone.now() > self.expires_at
        return False

    @property
    def days_until_expiry(self):
        """Get days until expiration."""
        from django.utils import timezone
        if self.status == self.Status.PENDING and self.expires_at:
            delta = self.expires_at - timezone.now()
            return max(0, delta.days)
        return None

    def time_until_expiration(self):
        """
        Get precise time until expiration.
        Returns timedelta or None.
        """
        from django.utils import timezone

        if self.status != self.Status.PENDING:
            return None

        # Use extended deadline if available
        deadline = self.expiration_extended_until or self.expires_at

        if not deadline:
            return None

        delta = deadline - timezone.now()
        return delta if delta.total_seconds() > 0 else None

    def can_expire(self):
        """
        Check if request can be expired.
        Returns True if request is pending and past deadline.
        """
        from django.utils import timezone

        if self.status != self.Status.PENDING:
            return False

        # Use extended deadline if available
        deadline = self.expiration_extended_until or self.expires_at

        if not deadline:
            return False

        return timezone.now() >= deadline

    @transaction.atomic
    def expire(self, expired_by_user=None):
        """
        Expire the transfer request.

        For RETURN requests: Revert item status to original (before PENDING_INSPECTION).
        For ASSIGN requests: Just expire without status change.

        Args:
            expired_by_user: User who manually expired (None for automatic expiration)

        Returns:
            bool: True if expired successfully
        """
        from django.utils import timezone

        # Validate
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot expire request with status {self.get_status_display()}.")

        # Lock the item to prevent race conditions
        from items.models import Item
        item = Item.objects.select_for_update().get(pk=self.item.pk)

        # Update request status
        self.status = self.Status.EXPIRED
        self.resolved_at = timezone.now()
        if expired_by_user:
            self.manually_expired_by = expired_by_user

        # Handle item status based on request type
        if self.request_type == self.RequestType.RETURN:
            # Revert to original status if we have it
            if self.original_item_status:
                # Only revert if item status hasn't been manually changed
                if item.status == 'PENDING_INSPECTION':
                    item.status = self.original_item_status
                    item.save()
            else:
                # Fallback: revert PENDING_INSPECTION to NORMAL
                if item.status == 'PENDING_INSPECTION':
                    item.status = 'NORMAL'
                    item.save()

        # For ASSIGN requests, just expire without changing item status

        self.save()
        return True

    def extend_expiration(self, days, extended_by_user):
        """
        Extend the expiration deadline.

        Args:
            days: Number of days to extend (from current deadline)
            extended_by_user: User extending the deadline (must be MANAGER)

        Returns:
            bool: True if extended successfully
        """
        from django.utils import timezone
        from datetime import timedelta

        # Validate permissions
        if not extended_by_user.is_manager:
            raise ValidationError("Only managers can extend expiration deadlines.")

        # Validate request is still pending
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot extend request with status {self.get_status_display()}.")

        # Calculate new deadline from current deadline (original or already extended)
        current_deadline = self.expiration_extended_until or self.expires_at

        if not current_deadline:
            raise ValidationError("Cannot extend request without expiration date.")

        # Set new extended deadline
        self.expiration_extended_until = current_deadline + timedelta(days=days)

        # Reset warning flags so warnings can be sent again
        self.warning_48h_sent = False
        self.warning_24h_sent = False

        self.save()
        return True

    def clean(self):
        """Validate transfer request."""
        super().clean()

        # Validate item is not inactive
        if self.item and self.item.is_inactive:
            raise ValidationError(
                f"Cannot transfer item {self.item.asset_id} with status '{self.item.get_status_display()}'. "
                f"Only items with status Normal, Damaged, or Pending Inspection can be transferred."
            )

        # Validate from_user owns the item (only for RETURN requests)
        # For ASSIGN requests, Staff can assign any available item to teachers
        if self.request_type == self.RequestType.RETURN and self.item and self.from_user_id:
            if self.from_user != self.item.current_owner:
                raise ValidationError(
                    f"User {self.from_user.email} does not own item {self.item.asset_id}. "
                    f"Current owner is {self.item.current_owner.email}."
                )

        # For returns, validate new_status is required when accepting
        if self.request_type == self.RequestType.RETURN and self.status == self.Status.ACCEPTED:
            if not self.new_status:
                raise ValidationError(
                    "New status is required when accepting a return request."
                )

    @transaction.atomic
    def accept(self, accepted_by_user, new_status=None, current_location=None):
        """
        Accept the transfer request.
        Updates item ownership and creates transfer log.

        Args:
            accepted_by_user: User accepting the request
            new_status: New status for return requests (required for RETURN)
            current_location: Location where item will be kept (required for ASSIGN)
        """
        from django.utils import timezone
        from items.models import Item

        # Validate
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot accept request that is {self.get_status_display()}.")

        # Validation depends on request type
        if self.request_type == self.RequestType.RETURN:
            # For returns: Any staff member can accept
            if not (accepted_by_user.is_staff_member or accepted_by_user.is_manager):
                raise ValidationError("Only staff members can accept return requests.")
            # Returns require new_status
            if not new_status:
                raise ValidationError("New status is required when accepting a return.")
        else:  # ASSIGN
            # For assigns: Only the assigned user can accept
            if accepted_by_user != self.to_user:
                raise ValidationError(f"Only {self.to_user.email} can accept this request.")
            # Assigns require current_location
            if not current_location:
                raise ValidationError("Current location is required when accepting an assignment.")

        # Update request status
        self.status = self.Status.ACCEPTED
        self.resolved_at = timezone.now()
        if new_status:
            self.new_status = new_status
        self.save()

        # Transfer item ownership
        old_owner = self.item.current_owner

        # For returns, item goes to whoever accepted it (any staff)
        # For assigns, item goes to the assigned user (to_user)
        if self.request_type == self.RequestType.RETURN:
            transfer_target = accepted_by_user
        else:
            transfer_target = self.to_user

        self.item.current_owner = transfer_target

        # Update item status if provided (for returns)
        if new_status:
            self.item.status = new_status

        # Update item current_location if provided (for assigns)
        if current_location:
            self.item.current_location = current_location

        self.item.save()

        # Create transfer log
        TransferLog.objects.create(
            item=self.item,
            from_user=old_owner,
            to_user=transfer_target,
            request=self,
            notes=self.notes or ''
        )

        return True

    @transaction.atomic
    def reject(self, rejected_by_user, reason=None):
        """
        Reject the transfer request.
        Reverts item to original state.
        """
        from django.utils import timezone

        # Validate
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot reject request that is {self.get_status_display()}.")

        # Validation depends on request type
        if self.request_type == self.RequestType.RETURN:
            # For returns: Any staff member can reject
            if not (rejected_by_user.is_staff_member or rejected_by_user.is_manager):
                raise ValidationError("Only staff members can reject return requests.")
        else:  # ASSIGN
            # For assigns: Only the assigned user can reject
            if rejected_by_user != self.to_user:
                raise ValidationError(f"Only {self.to_user.email} can reject this request.")

        # Update request status
        self.status = self.Status.REJECTED
        self.resolved_at = timezone.now()
        if reason:
            self.notes = f"{self.notes or ''}\n[REJECTED] {reason}".strip()
        self.save()

        # For returns, revert item status back to NORMAL (or original)
        if self.request_type == self.RequestType.RETURN:
            # If item was set to PENDING_INSPECTION, revert to NORMAL
            if self.item.status == 'PENDING_INSPECTION':
                self.item.status = 'NORMAL'
                self.item.save()

        return True


class TransferLog(models.Model):
    """
    Audit trail for all successful item transfers.
    Immutable record of ownership changes.
    """

    item = models.ForeignKey(
        'items.Item',
        on_delete=models.SET_NULL,  # Preserve audit trail even if item is deleted
        null=True,  # Allow null to preserve logs
        related_name='transfer_logs',
        verbose_name='Item'
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transfers_sent_logs',
        verbose_name='From User'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transfers_received_logs',
        verbose_name='To User'
    )
    request = models.ForeignKey(
        TransferRequest,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='logs',
        verbose_name='Transfer Request',
        help_text='Reference to original request (null for forced transfers)'
    )
    transferred_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    is_forced = models.BooleanField(
        default=False,
        verbose_name='Forced Transfer',
        help_text='True if this was a forced transfer by Admin'
    )

    class Meta:
        verbose_name = 'Transfer Log'
        verbose_name_plural = 'Transfer Logs'
        ordering = ['-transferred_at']
        indexes = [
            models.Index(fields=['item', '-transferred_at']),
            models.Index(fields=['from_user', '-transferred_at']),
            models.Index(fields=['to_user', '-transferred_at']),
        ]

    def __str__(self):
        forced = " [FORCED]" if self.is_forced else ""
        return f"{self.item.asset_id}: {self.from_user.email} → {self.to_user.email}{forced} ({self.transferred_at.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        """Override save to make logs immutable after creation."""
        if self.pk:
            raise ValidationError("Transfer logs cannot be modified after creation.")
        super().save(*args, **kwargs)
