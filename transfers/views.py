"""
Transfer workflow views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError

from users.decorators import staff_required, member_or_staff_required
from .models import TransferRequest, TransferLog
from .forms import TransferRequestForm, ReturnRequestForm, AcceptReturnForm, AcceptTransferForm, RejectRequestForm
from items.models import Item
from django.db.models import Count, Q
from notifications.utils import notify_new_request, notify_request_accepted, notify_request_rejected


@member_or_staff_required
def transfer_overview(request):
    """Transfer overview page with statistics."""

    # Count pending requests
    pending_to_accept = TransferRequest.objects.filter(
        to_user=request.user,
        status='PENDING'
    ).count()

    pending_sent = TransferRequest.objects.filter(
        from_user=request.user,
        status='PENDING'
    ).count()

    # Count total transfers
    total_completed = TransferRequest.objects.filter(
        status='ACCEPTED'
    ).count()

    # Recent activity
    recent_logs = TransferLog.objects.select_related(
        'item', 'from_user', 'to_user'
    ).order_by('-transferred_at')[:10]

    context = {
        'pending_to_accept': pending_to_accept,
        'pending_sent': pending_sent,
        'total_completed': total_completed,
        'recent_logs': recent_logs,
    }

    return render(request, 'transfers/transfer_overview.html', context)


@staff_required
def create_transfer_request(request):
    """Create a transfer request to assign item to member (Staff/Manager only)."""
    if request.method == 'POST':
        form = TransferRequestForm(request.POST, request_user=request.user)
        if form.is_valid():
            item = form.cleaned_data['item']

            # FR-2.4: Validate item status - cannot transfer inactive items
            if item.status in ['REPAIR', 'LOST', 'REMOVED']:
                messages.error(
                    request,
                    f"Cannot transfer item {item.asset_id}. "
                    f"Items with status '{item.get_status_display()}' cannot be transferred."
                )
                return redirect('items:item_detail', pk=item.pk)

            # Check if item already has a pending transfer request
            existing_pending = TransferRequest.objects.filter(
                item=item,
                status='PENDING'
            ).exists()

            if existing_pending:
                messages.error(
                    request,
                    f"Cannot create transfer request. Item {item.asset_id} already has a pending transfer request. "
                    f"Please wait for the existing request to be accepted or rejected first."
                )
                return redirect('transfers:create_transfer')

            transfer = form.save(commit=False)
            transfer.from_user = request.user
            transfer.request_type = 'ASSIGN'
            transfer.save()

            # Send notification to recipient
            notify_new_request(transfer)

            messages.success(
                request,
                f"Transfer request created. Waiting for {transfer.to_user.email} to accept."
            )
            return redirect('transfers:pending_requests')
    else:
        form = TransferRequestForm(request_user=request.user)

    context = {
        'form': form,
    }

    return render(request, 'transfers/create_transfer.html', context)


@member_or_staff_required
def create_return_request(request, item_id):
    """Create a return request (Member → Staff)."""
    item = get_object_or_404(Item, pk=item_id)

    # Verify user owns the item
    if item.current_owner != request.user:
        messages.error(request, "You can only return items you own.")
        return redirect('items:item_list')

    if request.method == 'POST':
        form = ReturnRequestForm(request.POST)
        if form.is_valid():
            # Find a staff member to return to
            from users.models import User
            staff_users = User.objects.filter(role__in=['STAFF', 'MANAGER'], is_active=True)
            if not staff_users.exists():
                messages.error(request, "No staff members available to receive return.")
                return redirect('items:item_detail', pk=item_id)

            # Create return request to first available staff
            transfer = TransferRequest.objects.create(
                request_type='RETURN',
                from_user=request.user,
                to_user=staff_users.first(),
                item=item,
                notes=form.cleaned_data.get('notes', '')
            )

            # Send notification to staff
            notify_new_request(transfer)

            # Set item status to pending inspection
            item.status = 'PENDING_INSPECTION'
            item.save()

            messages.success(
                request,
                f"Return request created for {item.asset_id}. "
                f"Waiting for staff to inspect and accept."
            )
            return redirect('core:dashboard')
    else:
        form = ReturnRequestForm()

    context = {
        'form': form,
        'item': item,
    }

    return render(request, 'transfers/create_return.html', context)


@member_or_staff_required
def pending_requests(request):
    """View all pending requests."""
    # Requests I need to handle (sent to me)
    # For STAFF/MANAGER: Show ALL pending RETURN requests (any staff can accept returns)
    #                    + ASSIGN requests specifically sent to them
    # For MEMBERS: Show only requests sent to them
    if request.user.is_staff_or_admin:
        # Staff can see all RETURN requests OR ASSIGN requests sent to them
        requests_to_accept = TransferRequest.objects.filter(
            Q(request_type='RETURN', status='PENDING') |  # All pending returns
            Q(to_user=request.user, request_type='ASSIGN', status='PENDING')  # Assigns to me
        ).select_related('item', 'from_user').order_by('-created_at')
    else:
        # Members only see requests sent to them
        requests_to_accept = TransferRequest.objects.filter(
            to_user=request.user,
            status='PENDING'
        ).select_related('item', 'from_user').order_by('-created_at')

    # Requests I sent (waiting for others)
    requests_sent = TransferRequest.objects.filter(
        from_user=request.user,
        status='PENDING'
    ).select_related('item', 'to_user').order_by('-created_at')

    context = {
        'requests_to_accept': requests_to_accept,
        'requests_sent': requests_sent,
    }

    return render(request, 'transfers/pending_requests.html', context)


@member_or_staff_required
def accept_request(request, pk):
    """Accept a transfer request."""
    transfer = get_object_or_404(TransferRequest, pk=pk)

    # Verify user can accept this request
    # For RETURN requests: Any staff member can accept
    # For ASSIGN requests: Only the assigned user can accept
    if transfer.request_type == 'RETURN':
        if not request.user.is_staff_or_admin:
            messages.error(request, "Only staff members can accept return requests.")
            return redirect('transfers:pending_requests')
    else:  # ASSIGN
        if transfer.to_user != request.user:
            messages.error(request, "You can only accept requests sent to you.")
            return redirect('transfers:pending_requests')

    if transfer.status != 'PENDING':
        messages.error(request, f"This request is already {transfer.get_status_display().lower()}.")
        return redirect('transfers:pending_requests')

    # For returns, require status selection
    if transfer.request_type == 'RETURN':
        if request.method == 'POST':
            form = AcceptReturnForm(request.POST)
            if form.is_valid():
                new_status = form.cleaned_data['new_status']
                try:
                    transfer.accept(request.user, new_status=new_status)

                    # Send notification to requester
                    notify_request_accepted(transfer)

                    messages.success(
                        request,
                        f"Return accepted. Item {transfer.item.asset_id} status set to {transfer.item.get_status_display()}."
                    )
                    return redirect('transfers:pending_requests')
                except ValidationError as e:
                    messages.error(request, str(e))
        else:
            form = AcceptReturnForm()

        context = {
            'transfer': transfer,
            'form': form,
        }
        return render(request, 'transfers/accept_return.html', context)

    # For assignments, require current_location
    if request.method == 'POST':
        form = AcceptTransferForm(request.POST)
        if form.is_valid():
            current_location = form.cleaned_data['current_location']
            try:
                transfer.accept(request.user, current_location=current_location)

                # Send notification to requester
                notify_request_accepted(transfer)

                messages.success(
                    request,
                    f"Transfer accepted. You now own {transfer.item.asset_id}."
                )
                return redirect('transfers:pending_requests')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = AcceptTransferForm()

    context = {
        'transfer': transfer,
        'form': form,
    }
    return render(request, 'transfers/accept_confirm.html', context)


@member_or_staff_required
def reject_request(request, pk):
    """Reject a transfer request."""
    transfer = get_object_or_404(TransferRequest, pk=pk)

    # Verify user can reject this request
    # For RETURN requests: Any staff member can reject
    # For ASSIGN requests: Only the assigned user can reject
    if transfer.request_type == 'RETURN':
        if not request.user.is_staff_or_admin:
            messages.error(request, "Only staff members can reject return requests.")
            return redirect('transfers:pending_requests')
    else:  # ASSIGN
        if transfer.to_user != request.user:
            messages.error(request, "You can only reject requests sent to you.")
            return redirect('transfers:pending_requests')

    if transfer.status != 'PENDING':
        messages.error(request, f"This request is already {transfer.get_status_display().lower()}.")
        return redirect('transfers:pending_requests')

    if request.method == 'POST':
        form = RejectRequestForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            try:
                transfer.reject(request.user, reason=reason)

                # Send notification to requester
                notify_request_rejected(transfer, reason)

                messages.success(
                    request,
                    f"Request rejected. {transfer.from_user.email} has been notified."
                )
                return redirect('transfers:pending_requests')
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('transfers:pending_requests')
    else:
        form = RejectRequestForm()

    context = {
        'transfer': transfer,
        'form': form,
    }
    return render(request, 'transfers/reject_confirm.html', context)


@staff_required
def transfer_history(request):
    """View transfer history (Staff/Manager only)."""
    from .models import TransferLog

    # Get all transfer logs
    logs = TransferLog.objects.all().select_related(
        'item', 'from_user', 'to_user'
    ).order_by('-transferred_at')

    context = {
        'logs': logs[:100],  # Limit to 100 most recent
    }

    return render(request, 'transfers/transfer_history.html', context)


@staff_required
def cancel_request(request, pk):
    """Cancel a pending transfer request (Staff/Manager only)."""
    transfer = get_object_or_404(TransferRequest, pk=pk)

    # Verify user can cancel this request
    # Must be staff/manager and involved in the request (sender or receiver)
    if transfer.from_user != request.user and transfer.to_user != request.user:
        messages.error(request, "You can only cancel requests you are involved in.")
        return redirect('transfers:pending_requests')

    if transfer.status != 'PENDING':
        messages.error(request, f"This request is already {transfer.get_status_display().lower()}.")
        return redirect('transfers:pending_requests')

    if request.method == 'POST':
        from .forms import CancelRequestForm
        form = CancelRequestForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get('reason', '')
            try:
                transfer.cancel(request.user, reason=reason)

                # Send notification to the other party
                from notifications.models import Notification
                other_user = transfer.to_user if transfer.from_user == request.user else transfer.from_user
                Notification.objects.create(
                    recipient=other_user,
                    notification_type='REQUEST_EXPIRED',  # Reuse EXPIRED type for cancelled
                    title='Transfer Request Cancelled',
                    message=f'{request.user.get_full_name() or request.user.email} cancelled a transfer request for {transfer.item.name}. {reason if reason else ""}',
                    related_request=transfer
                )

                messages.success(
                    request,
                    f"Request cancelled successfully."
                )
                return redirect('transfers:pending_requests')
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('transfers:pending_requests')
    else:
        from .forms import CancelRequestForm
        form = CancelRequestForm()

    context = {
        'transfer': transfer,
        'form': form,
    }
    return render(request, 'transfers/cancel_confirm.html', context)


@staff_required
def edit_request(request, pk):
    """Edit a pending transfer request (Staff/Manager only, requests sent by user)."""
    transfer = get_object_or_404(TransferRequest, pk=pk)

    # Verify user can edit this request
    # Can only edit requests they sent
    if transfer.from_user != request.user:
        messages.error(request, "You can only edit requests you sent.")
        return redirect('transfers:pending_requests')

    if transfer.status != 'PENDING':
        messages.error(request, f"Cannot edit request that is {transfer.get_status_display().lower()}.")
        return redirect('transfers:pending_requests')

    if request.method == 'POST':
        from .forms import EditTransferRequestForm
        form = EditTransferRequestForm(request.POST, instance=transfer, request_user=request.user)
        if form.is_valid():
            try:
                form.save()

                # Send notification about the change
                from notifications.models import Notification
                Notification.objects.create(
                    recipient=transfer.to_user,
                    notification_type='REQUEST_UPDATED',
                    title='Transfer Request Updated',
                    message=f'{request.user.get_full_name() or request.user.email} updated a transfer request for {transfer.item.name}.',
                    related_request=transfer
                )

                messages.success(
                    request,
                    f"Request updated successfully. {transfer.to_user.email} has been notified."
                )
                return redirect('transfers:pending_requests')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        from .forms import EditTransferRequestForm
        form = EditTransferRequestForm(instance=transfer, request_user=request.user)

    context = {
        'transfer': transfer,
        'form': form,
    }
    return render(request, 'transfers/edit_request.html', context)


@staff_required
def extend_request(request, pk):
    """Extend a pending transfer request deadline (Staff/Manager only)."""
    transfer = get_object_or_404(TransferRequest, pk=pk)

    # Verify user can extend this request
    # Can extend requests in both "Action Required" and "Requests Sent"
    if transfer.from_user != request.user and transfer.to_user != request.user:
        messages.error(request, "You can only extend requests you are involved in.")
        return redirect('transfers:pending_requests')

    if transfer.status != 'PENDING':
        messages.error(request, f"Cannot extend request that is {transfer.get_status_display().lower()}.")
        return redirect('transfers:pending_requests')

    if request.method == 'POST':
        from .forms import ExtendRequestForm
        form = ExtendRequestForm(request.POST)
        if form.is_valid():
            days = form.cleaned_data['days']
            notes = form.cleaned_data.get('notes', '')
            try:
                transfer.extend_expiration(days, request.user)

                # Send notification about the extension
                from notifications.models import Notification
                other_user = transfer.to_user if transfer.from_user == request.user else transfer.from_user
                Notification.objects.create(
                    recipient=other_user,
                    notification_type='REQUEST_EXTENDED',
                    title='Transfer Request Deadline Extended',
                    message=f'{request.user.get_full_name() or request.user.email} extended the deadline for {transfer.item.name} by {days} days. {notes if notes else ""}',
                    related_request=transfer
                )

                messages.success(
                    request,
                    f"Request deadline extended by {days} days. {other_user.email} has been notified."
                )
                return redirect('transfers:pending_requests')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        from .forms import ExtendRequestForm
        form = ExtendRequestForm()

    context = {
        'transfer': transfer,
        'form': form,
    }
    return render(request, 'transfers/extend_request.html', context)
