"""
Notification views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Notification


@login_required
def notification_list(request):
    """View all notifications for the current user."""
    # Get base queryset (without slicing)
    all_notifications = Notification.objects.filter(recipient=request.user)

    # Calculate statistics on unsliced queryset
    total_count = all_notifications.count()
    unread_count = all_notifications.filter(is_read=False).count()
    read_count = total_count - unread_count

    # Get limited notifications with related data for display
    notifications = all_notifications.select_related(
        'related_request__item', 'related_item'
    ).order_by('-created_at')[:50]

    context = {
        'notifications': notifications,
        'total_count': total_count,
        'unread_count': unread_count,
        'read_count': read_count,
    }

    return render(request, 'notifications/notification_list.html', context)


@login_required
@require_POST
def mark_as_read(request, pk):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()

    # Redirect back to referrer or notification list
    return redirect(request.META.get('HTTP_REFERER', 'notifications:list'))


@login_required
@require_POST
def mark_all_as_read(request):
    """Mark all notifications as read for current user."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    # Redirect back to referrer or notification list
    return redirect(request.META.get('HTTP_REFERER', 'notifications:list'))


@login_required
def get_unread_count_ajax(request):
    """AJAX endpoint to get unread notification count."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})
