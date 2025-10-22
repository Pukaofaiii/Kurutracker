"""
Core views for dashboard and home pages.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from items.models import Item
from transfers.models import TransferRequest
from .forms import ProfileEditForm


@login_required
def dashboard_view(request):
    """
    Main dashboard - redirects to role-specific dashboard.
    """
    user = request.user

    if user.role == 'TEACHER':
        return redirect('core:teacher_dashboard')
    elif user.role == 'STAFF':
        return redirect('core:staff_dashboard')
    elif user.role == 'MANAGER':
        return redirect('core:manager_dashboard')
    else:
        return redirect('account_login')


@login_required
def teacher_dashboard(request):
    """Dashboard for Teacher role."""
    user = request.user

    # Get teacher's items
    my_items = Item.objects.filter(current_owner=user)

    # Get pending requests (items being returned or assigned to me)
    pending_requests_received = TransferRequest.objects.filter(
        to_user=user,
        status='PENDING'
    ).select_related('item', 'from_user')

    pending_requests_sent = TransferRequest.objects.filter(
        from_user=user,
        status='PENDING'
    ).select_related('item', 'to_user')

    context = {
        'my_items': my_items,
        'my_items_count': my_items.count(),
        'pending_requests_received': pending_requests_received,
        'pending_requests_sent': pending_requests_sent,
        'pending_count': pending_requests_received.count(),
    }

    return render(request, 'core/dashboard_teacher.html', context)


@login_required
def staff_dashboard(request):
    """Dashboard for Staff role."""
    user = request.user

    # Get all items
    all_items = Item.objects.all()

    # Get items by status
    normal_items = all_items.filter(status='NORMAL').count()
    damaged_items = all_items.filter(status='DAMAGED').count()
    repair_items = all_items.filter(status='REPAIR').count()
    lost_items = all_items.filter(status='LOST').count()

    # Get pending transfer requests
    pending_requests = TransferRequest.objects.filter(
        status='PENDING'
    ).select_related('item', 'from_user', 'to_user')

    # Get requests I need to handle (sent to me)
    my_pending_requests = pending_requests.filter(to_user=user)

    # Get recent transfers
    recent_transfers = TransferRequest.objects.filter(
        status='ACCEPTED'
    ).select_related('item', 'from_user', 'to_user').order_by('-resolved_at')[:10]

    context = {
        'total_items': all_items.count(),
        'normal_items': normal_items,
        'damaged_items': damaged_items,
        'repair_items': repair_items,
        'lost_items': lost_items,
        'pending_requests': pending_requests,
        'my_pending_requests': my_pending_requests,
        'pending_count': my_pending_requests.count(),
        'recent_transfers': recent_transfers,
    }

    return render(request, 'core/dashboard_staff.html', context)


@login_required
def manager_dashboard(request):
    """Dashboard for Manager role."""
    from users.models import User

    # Get all items stats
    all_items = Item.objects.all()
    total_items = all_items.count()

    # Items by status
    items_by_status = {
        'normal': all_items.filter(status='NORMAL').count(),
        'damaged': all_items.filter(status='DAMAGED').count(),
        'repair': all_items.filter(status='REPAIR').count(),
        'lost': all_items.filter(status='LOST').count(),
        'pending_inspection': all_items.filter(status='PENDING_INSPECTION').count(),
        'removed': all_items.filter(status='REMOVED').count(),
    }

    # User stats
    total_users = User.objects.filter(is_active=True).count()
    teachers = User.objects.filter(role='TEACHER', is_active=True).count()
    staff = User.objects.filter(role='STAFF', is_active=True).count()
    admins = User.objects.filter(role='MANAGER', is_active=True).count()

    # Transfer stats
    pending_transfers = TransferRequest.objects.filter(status='PENDING').count()
    total_transfers = TransferRequest.objects.filter(status='ACCEPTED').count()

    # Users with most items
    users_with_items = User.objects.annotate(
        item_count=Count('current_items', filter=Q(current_items__status__in=['NORMAL', 'DAMAGED', 'PENDING_INSPECTION']))
    ).filter(item_count__gt=0).order_by('-item_count')[:10]

    # Recent activity
    recent_transfers = TransferRequest.objects.filter(
        status='ACCEPTED'
    ).select_related('item', 'from_user', 'to_user').order_by('-resolved_at')[:15]

    context = {
        'total_items': total_items,
        'items_by_status': items_by_status,
        'total_users': total_users,
        'teachers': teachers,
        'staff': staff,
        'admins': admins,
        'pending_transfers': pending_transfers,
        'total_transfers': total_transfers,
        'users_with_items': users_with_items,
        'recent_transfers': recent_transfers,
    }

    return render(request, 'core/dashboard_manager.html', context)


@login_required
def account_settings(request):
    """User account settings page."""
    user = request.user

    context = {
        'user_obj': user,
    }

    return render(request, 'core/account_settings.html', context)


@login_required
def edit_profile(request):
    """Edit user's own profile information."""
    user = request.user

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('core:account_settings')
    else:
        form = ProfileEditForm(instance=user)

    context = {
        'form': form,
        'user_obj': user,
    }

    return render(request, 'core/edit_profile.html', context)
