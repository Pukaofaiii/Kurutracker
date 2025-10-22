"""
Context processors for notifications.
"""

from .models import Notification


def unread_notifications(request):
    """
    Add unread notification count to template context.
    """
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()

        recent_notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related('related_request__item').order_by('-created_at')[:5]
    else:
        unread_count = 0
        recent_notifications = []

    return {
        'unread_notification_count': unread_count,
        'recent_notifications': recent_notifications,
    }
