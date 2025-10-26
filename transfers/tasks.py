"""
Celery tasks for transfers app.

Handles automatic request expiration with dual warning system:
- 48-hour warning
- 24-hour warning
- Automatic expiration after 7 days
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

from .models import TransferRequest
from notifications.utils import notify_request_expiring_soon, notify_request_expired

logger = logging.getLogger(__name__)


@shared_task
def check_expiring_requests():
    """
    Check for expiring transfer requests and take appropriate action:
    1. Send 48-hour warning (if not already sent)
    2. Send 24-hour warning (if not already sent)
    3. Auto-expire requests past deadline

    Runs daily via Celery Beat.

    Returns:
        dict: Statistics about warnings sent and requests expired
    """
    now = timezone.now()

    stats = {
        'warnings_48h': 0,
        'warnings_24h': 0,
        'expired': 0,
        'errors': 0
    }

    # Get all pending requests
    pending_requests = TransferRequest.objects.filter(
        status=TransferRequest.Status.PENDING
    ).select_related('item', 'to_user', 'from_user')

    for request in pending_requests:
        try:
            # Determine effective deadline (extended or original)
            deadline = request.expiration_extended_until or request.expires_at

            if not deadline:
                continue

            time_until_expiry = deadline - now
            hours_remaining = time_until_expiry.total_seconds() / 3600

            # Check if request should be expired
            if hours_remaining <= 0:
                _expire_request(request)
                stats['expired'] += 1

            # Send 24-hour warning (if between 24-25 hours remaining and not sent)
            elif 24 <= hours_remaining < 25 and not request.warning_24h_sent:
                notify_request_expiring_soon(request, hours_remaining=24)
                request.warning_24h_sent = True
                request.save(update_fields=['warning_24h_sent', 'updated_at'])
                stats['warnings_24h'] += 1
                logger.info(f"Sent 24h warning for request {request.pk}")

            # Send 48-hour warning (if between 48-49 hours remaining and not sent)
            elif 48 <= hours_remaining < 49 and not request.warning_48h_sent:
                notify_request_expiring_soon(request, hours_remaining=48)
                request.warning_48h_sent = True
                request.save(update_fields=['warning_48h_sent', 'updated_at'])
                stats['warnings_48h'] += 1
                logger.info(f"Sent 48h warning for request {request.pk}")

        except Exception as e:
            stats['errors'] += 1
            logger.error(f"Error processing request {request.pk}: {str(e)}")
            continue

    result_msg = (
        f"Expiration check complete: "
        f"{stats['warnings_48h']} 48h warnings, "
        f"{stats['warnings_24h']} 24h warnings, "
        f"{stats['expired']} expired, "
        f"{stats['errors']} errors"
    )
    logger.info(result_msg)

    return result_msg


@transaction.atomic
def _expire_request(request):
    """
    Helper function to expire a single request with race condition protection.

    Uses select_for_update() to lock the request and item during expiration.

    Args:
        request: TransferRequest instance to expire
    """
    # Lock request to prevent concurrent modification
    locked_request = TransferRequest.objects.select_for_update().get(pk=request.pk)

    # Double-check status (race condition protection)
    if locked_request.status != TransferRequest.Status.PENDING:
        logger.warning(f"Request {request.pk} already resolved, skipping expiration")
        return

    # Use the model's expire() method which handles all logic
    try:
        locked_request.expire(expired_by_user=None)

        # Send notifications
        notify_request_expired(locked_request)

        logger.info(
            f"Expired request {locked_request.pk}: "
            f"{locked_request.get_request_type_display()} for {locked_request.item.asset_id}"
        )
    except Exception as e:
        logger.error(f"Error expiring request {request.pk}: {str(e)}")
        raise
