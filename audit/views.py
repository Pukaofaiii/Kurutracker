"""
Audit views for item inspection and tracking.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.db import transaction

from users.decorators import auditor_required, auditor_or_manager_required
from items.models import Item, ItemCategory
from transfers.models import TransferRequest, TransferLog
from locations.models import Location, Room
from users.models import User
from notifications.utils import create_notification, send_notification_email
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count
from datetime import datetime, timedelta


@auditor_required
def audit_checklist(request):
    """
    Audit checklist view - Shows all active items with filters.
    Auditors can filter by location, status, owner, category, or room.
    """
    # Get all items except REMOVED
    items = Item.objects.exclude(status='REMOVED').select_related(
        'current_owner',
        'home_base_location',
        'current_location',
        'category',
        'room'
    ).order_by('asset_id')

    # Apply filters
    location_filter = request.GET.get('location')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    category_filter = request.GET.get('category')
    room_filter = request.GET.get('room')
    owner_filter = request.GET.get('owner')

    if location_filter:
        items = items.filter(
            Q(home_base_location_id=location_filter) |
            Q(current_location_id=location_filter)
        )

    if status_filter:
        items = items.filter(status=status_filter)

    if category_filter:
        items = items.filter(category_id=category_filter)

    if room_filter:
        items = items.filter(room_id=room_filter)

    if owner_filter:
        items = items.filter(current_owner_id=owner_filter)

    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(asset_id__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(current_owner__email__icontains=search_query)
        )

    # Get filter choices
    locations = Location.objects.filter(is_active=True).order_by('building', 'floor', 'room')
    categories = ItemCategory.objects.all().order_by('name')
    rooms = Room.objects.filter(is_active=True).order_by('code')
    owners = User.objects.filter(is_active=True).order_by('email')

    # Statistics
    total_items = Item.objects.exclude(status='REMOVED').count()
    normal_count = Item.objects.filter(status='NORMAL').count()
    damaged_count = Item.objects.filter(status='DAMAGED').count()
    repair_count = Item.objects.filter(status='REPAIR').count()
    lost_count = Item.objects.filter(status='LOST').count()
    pending_count = Item.objects.filter(status='PENDING_INSPECTION').count()

    context = {
        'items': items,
        'locations': locations,
        'categories': categories,
        'rooms': rooms,
        'owners': owners,
        'location_filter': location_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'category_filter': category_filter,
        'room_filter': room_filter,
        'owner_filter': owner_filter,
        'statuses': Item.Status.choices,
        'total_items': total_items,
        'normal_count': normal_count,
        'damaged_count': damaged_count,
        'repair_count': repair_count,
        'lost_count': lost_count,
        'pending_count': pending_count,
    }

    return render(request, 'audit/audit_checklist.html', context)


@auditor_required
def audit_mark_damaged(request, item_id):
    """
    Mark item as damaged and auto-create return request to staff.
    This triggers the return workflow for inspection by staff.
    """
    item = get_object_or_404(Item, pk=item_id)

    # Check if user has permission to audit this item
    if not request.user.can_audit_item(item):
        messages.error(
            request,
            f"You don't have permission to audit item {item.asset_id}. "
            "Contact your manager for auditor assignment."
        )
        return redirect('audit:audit_checklist')

    # Validate item can be marked as damaged
    if item.status == 'LOST':
        messages.error(request, f"Cannot mark lost item {item.asset_id} as damaged. Use 'Found' workflow first.")
        return redirect('audit:audit_checklist')

    if item.status == 'REMOVED':
        messages.error(request, f"Cannot mark removed item {item.asset_id} as damaged.")
        return redirect('audit:audit_checklist')

    if request.method == 'POST':
        notes = request.POST.get('notes', '')

        try:
            with transaction.atomic():
                # Set item status to PENDING_INSPECTION
                item.status = 'PENDING_INSPECTION'
                item.save()

                # Auto-create return request from current owner to auditor (staff)
                transfer_request = TransferRequest.objects.create(
                    request_type=TransferRequest.RequestType.RETURN,
                    from_user=item.current_owner,
                    to_user=request.user,
                    item=item,
                    notes=f"[AUDIT] Item reported as damaged by auditor {request.user.email}.\n{notes}",
                    new_status='DAMAGED'  # Default to DAMAGED, staff can change when accepting
                )

                # Notify current owner
                create_notification(
                    recipient=item.current_owner,
                    notification_type='ITEM_DAMAGED',
                    title=f'Audit: Item {item.asset_id} Marked as Damaged',
                    message=f'Auditor has identified your item "{item.name}" as damaged. A return request has been created for inspection.',
                    related_request=transfer_request,
                    related_item=item
                )
                send_notification_email(
                    recipient=item.current_owner,
                    subject=f'Audit: Item {item.asset_id} Marked as Damaged',
                    template='notifications/emails/item_damaged.html',
                    context={
                        'item': item,
                        'transfer_request': transfer_request,
                        'notes': notes,
                    }
                )

                messages.success(
                    request,
                    f"Item {item.asset_id} marked as damaged. Return request created for {item.current_owner.email}."
                )
                return redirect('audit:audit_checklist')

        except Exception as e:
            messages.error(request, f"Error marking item as damaged: {str(e)}")
            return redirect('audit:audit_checklist')

    context = {
        'item': item,
    }

    return render(request, 'audit/mark_damaged_confirm.html', context)


@auditor_required
def audit_mark_lost(request, item_id):
    """
    Mark item as LOST.
    Item remains assigned to current owner (keeps them accountable).
    """
    item = get_object_or_404(Item, pk=item_id)

    # Check if user has permission to audit this item
    if not request.user.can_audit_item(item):
        messages.error(
            request,
            f"You don't have permission to audit item {item.asset_id}. "
            "Contact your manager for auditor assignment."
        )
        return redirect('audit:audit_checklist')

    # Validate item can be marked as lost
    if item.status == 'REMOVED':
        messages.error(request, f"Cannot mark removed item {item.asset_id} as lost.")
        return redirect('audit:audit_checklist')

    if item.status == 'LOST':
        messages.warning(request, f"Item {item.asset_id} is already marked as lost.")
        return redirect('audit:audit_lost_items')

    if request.method == 'POST':
        notes = request.POST.get('notes', '')

        try:
            # Set item status to LOST (keeps current owner)
            item.status = 'LOST'
            item.save()

            # Notify current owner
            create_notification(
                recipient=item.current_owner,
                notification_type='ITEM_LOST',
                title=f'Audit: Item {item.asset_id} Marked as Lost',
                message=f'Auditor has marked your item "{item.name}" as LOST. You are still responsible for this item until it is found or written off.',
                related_item=item
            )
            send_notification_email(
                recipient=item.current_owner,
                subject=f'Audit: Item {item.asset_id} Marked as LOST',
                template='notifications/emails/item_lost.html',
                context={
                    'item': item,
                    'notes': notes,
                }
            )

            messages.success(
                request,
                f"Item {item.asset_id} marked as LOST. Owner {item.current_owner.email} remains accountable."
            )
            return redirect('audit:audit_lost_items')

        except Exception as e:
            messages.error(request, f"Error marking item as lost: {str(e)}")
            return redirect('audit:audit_checklist')

    context = {
        'item': item,
    }

    return render(request, 'audit/mark_lost_confirm.html', context)


@auditor_required
def audit_lost_items(request):
    """
    View all lost items.
    Shows who is responsible for each lost item.
    """
    lost_items = Item.objects.filter(
        status='LOST'
    ).select_related(
        'current_owner',
        'home_base_location',
        'current_location'
    ).order_by('-updated_at')

    # Statistics
    total_lost = lost_items.count()

    context = {
        'lost_items': lost_items,
        'total_lost': total_lost,
    }

    return render(request, 'audit/lost_items.html', context)


@auditor_required
def audit_found_item(request, item_id):
    """
    Recovery workflow for found lost items.
    Requires condition assessment before returning to system.
    """
    item = get_object_or_404(Item, pk=item_id)

    # Check if user has permission to audit this item
    if not request.user.can_audit_item(item):
        messages.error(
            request,
            f"You don't have permission to audit item {item.asset_id}. "
            "Contact your manager for auditor assignment."
        )
        return redirect('audit:audit_checklist')

    # Validate item is lost
    if item.status != 'LOST':
        messages.error(request, f"Item {item.asset_id} is not marked as lost.")
        return redirect('audit:audit_checklist')

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        notes = request.POST.get('notes', '')

        if new_status not in ['NORMAL', 'DAMAGED', 'REPAIR']:
            messages.error(request, "Invalid status selected.")
            return redirect('audit:found_item', item_id=item_id)

        try:
            with transaction.atomic():
                # Update item status
                old_owner = item.current_owner
                item.status = new_status
                item.save()

                # Notify old owner that item was found
                create_notification(
                    recipient=old_owner,
                    notification_type='ITEM_FOUND',
                    title=f'Item {item.asset_id} Found',
                    message=f'Good news! Your lost item "{item.name}" has been found and assessed as {item.get_status_display()}.',
                    related_item=item
                )
                send_notification_email(
                    recipient=old_owner,
                    subject=f'Item {item.asset_id} Found',
                    template='notifications/emails/item_found.html',
                    context={
                        'item': item,
                        'new_status': item.get_status_display(),
                        'notes': notes,
                    }
                )

                messages.success(
                    request,
                    f"Item {item.asset_id} recovered and marked as {item.get_status_display()}. Owner {old_owner.email} has been notified."
                )
                return redirect('audit:audit_checklist')

        except Exception as e:
            messages.error(request, f"Error recovering item: {str(e)}")
            return redirect('audit:found_item', item_id=item_id)

    context = {
        'item': item,
    }

    return render(request, 'audit/found_item.html', context)


@auditor_required
@require_POST
def update_item_status(request, pk):
    """
    AJAX view to update item status from audit checklist.
    Allows quick status updates for audits.
    """
    item = get_object_or_404(Item, pk=pk)

    # Check if user has permission to audit this item
    if not request.user.can_audit_item(item):
        return JsonResponse({
            'success': False,
            'error': f'You don\'t have permission to audit item {item.asset_id}'
        }, status=403)

    new_status = request.POST.get('status')

    if new_status not in dict(Item.Status.choices).keys():
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

    old_status = item.status
    item.status = new_status
    item.save()

    return JsonResponse({
        'success': True,
        'message': f'Item {item.asset_id} status updated from {old_status} to {new_status}',
        'old_status': old_status,
        'new_status': new_status,
    })


@auditor_or_manager_required
def audit_report(request):
    """
    Generate comprehensive audit reports with statistics and filters.
    Shows overall system health and items needing attention.
    """
    # Get date range filter (default: last 30 days)
    days = int(request.GET.get('days', 30))
    start_date = datetime.now() - timedelta(days=days)

    # Item statistics
    total_items = Item.objects.exclude(status='REMOVED').count()
    status_counts = {}
    for status_code, status_label in Item.Status.choices:
        if status_code != 'REMOVED':
            count = Item.objects.filter(status=status_code).count()
            status_counts[status_label] = {
                'count': count,
                'percentage': round((count / total_items * 100) if total_items > 0 else 0, 1)
            }

    # Category statistics with percentages
    category_stats_raw = ItemCategory.objects.annotate(
        item_count=Count('items', filter=~Q(items__status='REMOVED'))
    ).order_by('-item_count')

    # Add percentage to each category
    category_stats = []
    for cat in category_stats_raw:
        category_stats.append({
            'name': cat.name,
            'item_count': cat.item_count,
            'percentage': round((cat.item_count / total_items * 100) if total_items > 0 else 0, 1)
        })

    # Owner statistics with percentages
    owner_stats_raw = User.objects.filter(is_active=True).annotate(
        item_count=Count('current_items', filter=~Q(current_items__status='REMOVED'))
    ).filter(item_count__gt=0).order_by('-item_count')[:20]

    owner_stats = []
    for owner in owner_stats_raw:
        owner_stats.append({
            'owner': owner,
            'item_count': owner.item_count,
            'percentage': round((owner.item_count / total_items * 100) if total_items > 0 else 0, 1)
        })

    # Room statistics with percentages
    room_stats_raw = Room.objects.filter(is_active=True).annotate(
        item_count=Count('items', filter=~Q(items__status='REMOVED'))
    ).filter(item_count__gt=0).order_by('-item_count')[:20]

    room_stats = []
    for room in room_stats_raw:
        room_stats.append({
            'room': room,
            'item_count': room.item_count,
            'percentage': round((room.item_count / total_items * 100) if total_items > 0 else 0, 1)
        })

    # Recent transfers
    recent_transfers = TransferLog.objects.filter(
        transferred_at__gte=start_date
    ).select_related('item', 'from_user', 'to_user').order_by('-transferred_at')[:30]

    # Items needing attention (damaged, lost, repair, pending inspection)
    items_needing_attention = Item.objects.filter(
        status__in=['DAMAGED', 'LOST', 'REPAIR', 'PENDING_INSPECTION']
    ).select_related('current_owner', 'category', 'room').order_by('status', 'asset_id')

    context = {
        'days': days,
        'start_date': start_date,
        'total_items': total_items,
        'status_counts': status_counts,
        'category_stats': category_stats,
        'owner_stats': owner_stats,
        'room_stats': room_stats,
        'recent_transfers': recent_transfers,
        'items_needing_attention': items_needing_attention,
    }
    return render(request, 'audit/audit_report.html', context)
