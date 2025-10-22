"""
Notification helper functions.
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Notification


def create_notification(recipient, notification_type, title, message, related_request=None, related_item=None):
    """
    Create a new notification for a user.

    Args:
        recipient: User to receive the notification
        notification_type: Type from Notification.NotificationType choices
        title: Notification title
        message: Notification message
        related_request: Optional TransferRequest object
        related_item: Optional Item object

    Returns:
        Notification object
    """
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_request=related_request,
        related_item=related_item
    )
    return notification


def send_notification_email(recipient, subject, template_name, context):
    """
    Send an email notification to a user.

    Args:
        recipient: User to receive the email
        subject: Email subject
        template_name: Template file name (e.g., 'new_request.html')
        context: Dictionary of template context variables

    Returns:
        Number of emails sent (0 or 1)
    """
    # Add base URL to context for email links
    context['site_url'] = getattr(settings, 'SITE_URL', 'http://localhost:8000')

    # Render HTML email
    html_message = render_to_string(f'notifications/emails/{template_name}', context)

    # Send email
    try:
        send_mail(
            subject=subject,
            message='',  # Plain text version (empty, using HTML)
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            html_message=html_message,
            fail_silently=False,
        )
        return 1
    except Exception as e:
        print(f"Error sending email to {recipient.email}: {e}")
        return 0


def notify_new_request(transfer_request):
    """
    Notify user about a new transfer request.
    Creates both in-app notification and sends email.
    """
    recipient = transfer_request.to_user
    request_type = transfer_request.get_request_type_display()

    # Create in-app notification
    title = f"New {request_type} Request"
    message = f"{transfer_request.from_user.get_full_name()} wants to {request_type.lower()} {transfer_request.item.asset_id} - {transfer_request.item.name}."

    create_notification(
        recipient=recipient,
        notification_type=Notification.NotificationType.NEW_REQUEST,
        title=title,
        message=message,
        related_request=transfer_request
    )

    # Send email notification
    subject = f"[Kurutracker] {title}"
    context = {
        'recipient': recipient,
        'transfer_request': transfer_request,
        'request_type': request_type,
    }
    send_notification_email(recipient, subject, 'new_request.html', context)


def notify_request_accepted(transfer_request):
    """Notify user that their request was accepted."""
    recipient = transfer_request.from_user

    title = "Request Accepted"
    message = f"{transfer_request.to_user.get_full_name()} accepted your request for {transfer_request.item.asset_id} - {transfer_request.item.name}."

    create_notification(
        recipient=recipient,
        notification_type=Notification.NotificationType.REQUEST_ACCEPTED,
        title=title,
        message=message,
        related_request=transfer_request
    )

    # Send email
    subject = f"[Kurutracker] {title}"
    context = {
        'recipient': recipient,
        'transfer_request': transfer_request,
    }
    send_notification_email(recipient, subject, 'request_accepted.html', context)


def notify_request_rejected(transfer_request, reason):
    """Notify user that their request was rejected."""
    recipient = transfer_request.from_user

    title = "Request Rejected"
    message = f"{transfer_request.to_user.get_full_name()} rejected your request for {transfer_request.item.asset_id}. Reason: {reason}"

    create_notification(
        recipient=recipient,
        notification_type=Notification.NotificationType.REQUEST_REJECTED,
        title=title,
        message=message,
        related_request=transfer_request
    )

    # Send email
    subject = f"[Kurutracker] {title}"
    context = {
        'recipient': recipient,
        'transfer_request': transfer_request,
        'reason': reason,
    }
    send_notification_email(recipient, subject, 'request_rejected.html', context)


def notify_request_expiring_soon(transfer_request, days_remaining):
    """Notify user that their pending request is expiring soon."""
    recipient = transfer_request.to_user

    title = "Request Expiring Soon"
    message = f"You have a pending request for {transfer_request.item.asset_id} that will expire in {days_remaining} days."

    create_notification(
        recipient=recipient,
        notification_type=Notification.NotificationType.REQUEST_EXPIRING_SOON,
        title=title,
        message=message,
        related_request=transfer_request
    )

    # Send email
    subject = f"[Kurutracker] {title} - Action Required"
    context = {
        'recipient': recipient,
        'transfer_request': transfer_request,
        'days_remaining': days_remaining,
    }
    send_notification_email(recipient, subject, 'request_expiring_soon.html', context)


def notify_request_expired(transfer_request):
    """Notify users that a request has expired and been auto-cancelled."""
    # Notify both sender and recipient
    for user in [transfer_request.from_user, transfer_request.to_user]:
        title = "Request Expired"
        message = f"Transfer request for {transfer_request.item.asset_id} has expired and been automatically cancelled."

        create_notification(
            recipient=user,
            notification_type=Notification.NotificationType.REQUEST_EXPIRED,
            title=title,
            message=message,
            related_request=transfer_request
        )

        # Send email
        subject = f"[Kurutracker] {title}"
        context = {
            'recipient': user,
            'transfer_request': transfer_request,
        }
        send_notification_email(user, subject, 'request_expired.html', context)


def get_unread_count(user):
    """Get count of unread notifications for a user."""
    return Notification.objects.filter(recipient=user, is_read=False).count()
