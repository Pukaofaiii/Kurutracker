"""
Celery tasks for transfers app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import TransferRequest
from notifications.utils import notify_request_expiring_soon, notify_request_expired


@shared_task
def expire_old_requests():
    """
    Expire transfer requests that are older than 7 days.
    Runs daily via Celery Beat.
    """
    now = timezone.now()

    # Find all PENDING requests that have expired
    expired_requests = TransferRequest.objects.filter(
        status=TransferRequest.Status.PENDING,
        expires_at__lt=now
    )

    expired_count = 0
    for request in expired_requests:
        # Mark as REJECTED
        request.status = TransferRequest.Status.REJECTED
        request.resolved_at = now
        request.notes = f"{request.notes or ''}\n[AUTO-EXPIRED] Request expired after 7 days without response.".strip()
        request.save()

        # Revert item status if it was PENDING_INSPECTION
        if request.request_type == 'RETURN' and request.item.status == 'PENDING_INSPECTION':
            request.item.status = 'NORMAL'
            request.item.save()

        # Notify both parties
        notify_request_expired(request)
        expired_count += 1

    return f"Expired {expired_count} old requests"


@shared_task
def send_expiration_reminders():
    """
    Send reminder emails for requests expiring in 1-2 days.
    Runs daily via Celery Beat.
    """
    now = timezone.now()
    reminder_window_start = now + timedelta(days=1)
    reminder_window_end = now + timedelta(days=2)

    # Find requests expiring in 1-2 days
    expiring_requests = TransferRequest.objects.filter(
        status=TransferRequest.Status.PENDING,
        expires_at__gte=reminder_window_start,
        expires_at__lte=reminder_window_end
    )

    reminder_count = 0
    for request in expiring_requests:
        days_remaining = request.days_until_expiry
        if days_remaining is not None:
            notify_request_expiring_soon(request, days_remaining)
            reminder_count += 1

    return f"Sent {reminder_count} expiration reminders"
