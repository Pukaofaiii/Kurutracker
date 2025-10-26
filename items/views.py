"""
Item management views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q

from users.decorators import staff_required, owns_item_or_staff, teacher_or_staff_required
from .models import Item, ItemCategory
from .forms import ItemForm, ItemFilterForm, CategoryForm, UpdateLocationForm


@teacher_or_staff_required
def item_list(request):
    """List all items with filtering."""
    items = Item.objects.all().select_related('category', 'current_owner')

    # Apply filters
    form = ItemFilterForm(request.GET)
    if form.is_valid():
        search = form.cleaned_data.get('search')
        if search:
            items = items.filter(
                Q(name__icontains=search) |
                Q(asset_id__icontains=search) |
                Q(model__icontains=search)
            )

        category = form.cleaned_data.get('category')
        if category:
            items = items.filter(category=category)

        status = form.cleaned_data.get('status')
        if status:
            items = items.filter(status=status)

        owner = form.cleaned_data.get('owner')
        if owner:
            items = items.filter(current_owner_id=owner)

    # If user is Teacher, only show their own items
    if request.user.is_teacher:
        items = items.filter(current_owner=request.user)

    # Hide removed items if filter is checked
    if request.GET.get('hide_removed'):
        items = items.exclude(status='REMOVED')

    # Get all categories for the filter dropdown
    categories = ItemCategory.objects.all()

    context = {
        'items': items,
        'form': form,
        'categories': categories,
    }

    return render(request, 'items/item_list.html', context)


@staff_required
def item_create(request):
    """Create a new item (Staff/Admin only)."""
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save()
            messages.success(
                request,
                f"Item {item.asset_id} - {item.name} created successfully."
            )
            return redirect('items:item_list')
    else:
        # Set default current_owner to request.user
        form = ItemForm(initial={'current_owner': request.user})

    context = {
        'form': form,
        'action': 'Create',
    }

    return render(request, 'items/item_form.html', context)


@teacher_or_staff_required
def item_detail(request, pk):
    """View item details."""
    item = get_object_or_404(Item, pk=pk)

    # Teachers can only view their own items
    if request.user.is_teacher and item.current_owner != request.user:
        messages.error(request, "You can only view items you own.")
        return redirect('items:item_list')

    # Get transfer history
    transfer_history = item.get_transfer_history()

    # Get current pending transfer (if any)
    pending_transfer = item.get_current_transfer_request()

    context = {
        'item': item,
        'transfer_history': transfer_history,
        'pending_transfer': pending_transfer,
    }

    return render(request, 'items/item_detail.html', context)


@staff_required
def item_update(request, pk):
    """Update an existing item (Staff/Admin only)."""
    item = get_object_or_404(Item, pk=pk)

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(
                request,
                f"Item {item.asset_id} - {item.name} updated successfully."
            )
            return redirect('items:item_update', pk=item.pk)
    else:
        form = ItemForm(instance=item)

    # Get transfer history
    transfer_history = item.get_transfer_history()

    context = {
        'form': form,
        'item': item,
        'transfer_history': transfer_history,
        'action': 'Update',
    }

    return render(request, 'items/item_form.html', context)


@staff_required
def item_delete(request, pk):
    """Mark item as REMOVED or permanently delete (Manager only for hard delete)."""
    item = get_object_or_404(Item, pk=pk)

    if request.method == 'POST':
        asset_id = item.asset_id
        name = item.name
        delete_type = request.POST.get('delete_type', 'soft')

        # Check if hard delete is requested
        if delete_type == 'hard':
            # Only managers can hard delete
            if not request.user.is_manager:
                messages.error(
                    request,
                    "Only managers can permanently delete items."
                )
                return redirect('items:item_update', pk=pk)

            # Get transfer history count before deleting
            transfer_count = item.transfer_logs.count()

            # Hard delete: Permanently remove from database
            item.delete()

            messages.success(
                request,
                f"Item {asset_id} - {name} has been permanently deleted from the database. "
                f"{transfer_count} transfer log(s) were also removed."
            )
        else:
            # Soft delete: Mark as REMOVED instead of deleting
            item.status = 'REMOVED'
            item.save()

            messages.success(
                request,
                f"Item {asset_id} - {name} has been marked as REMOVED and removed from active circulation."
            )

        return redirect('items:item_list')

    # Get transfer history count for display
    transfer_count = item.transfer_logs.count()

    context = {
        'item': item,
        'transfer_count': transfer_count,
    }

    return render(request, 'items/item_confirm_delete.html', context)


@owns_item_or_staff
def update_item_location(request, pk):
    """Update current location of an item (Owner can update their own items)."""
    item = get_object_or_404(Item, pk=pk)

    # Verify user owns the item or is staff
    if not request.user.is_staff_or_admin and item.current_owner != request.user:
        messages.error(request, "You can only update locations for items you own.")
        return redirect('items:item_update', pk=pk)

    if request.method == 'POST':
        form = UpdateLocationForm(request.POST)
        if form.is_valid():
            item.current_location = form.cleaned_data['current_location']
            item.save()
            messages.success(
                request,
                f"Location updated for {item.asset_id} - {item.name}."
            )
            return redirect('items:item_update', pk=pk)
    else:
        # Pre-populate with current location if exists
        initial_data = {}
        if item.current_location:
            initial_data['current_location'] = item.current_location
        form = UpdateLocationForm(initial=initial_data)

    context = {
        'form': form,
        'item': item,
    }

    return render(request, 'items/update_location.html', context)


@staff_required
def category_list(request):
    """List all categories (Staff/Admin only)."""
    categories = ItemCategory.objects.all()

    context = {
        'categories': categories,
    }

    return render(request, 'items/category_list.html', context)


@staff_required
def category_create(request):
    """Create a new category (Staff/Admin only)."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(
                request,
                f"Category '{category.name}' created successfully."
            )
            return redirect('items:category_list')
    else:
        form = CategoryForm()

    context = {
        'form': form,
        'action': 'Create',
    }

    return render(request, 'items/category_form.html', context)


@staff_required
def bulk_delete_items(request):
    """Soft delete (mark as REMOVED) multiple items at once (Staff/Admin only)."""
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids')

        if not item_ids:
            messages.error(request, "No items selected for deletion.")
            return redirect('items:item_list')

        # Check if this is the confirmation step
        if 'confirm' in request.POST:
            from django.db import transaction
            from django.utils import timezone

            with transaction.atomic():
                # Lock rows for update to prevent race conditions
                items = Item.objects.filter(pk__in=item_ids).select_for_update()
                count = items.count()

                # Soft delete: Mark all as REMOVED
                items.update(status='REMOVED', updated_at=timezone.now())

            messages.success(
                request,
                f"{count} item(s) have been marked as REMOVED and removed from active circulation."
            )
            return redirect('items:item_list')

        # Show confirmation page
        items = Item.objects.filter(pk__in=item_ids)

        context = {
            'items': items,
            'item_ids': item_ids,
        }

        return render(request, 'items/bulk_delete_confirm.html', context)

    return redirect('items:item_list')


@staff_required
def bulk_update_status(request):
    """Change status for multiple items at once (Staff/Admin only)."""
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids')

        if not item_ids:
            messages.error(request, "No items selected for status change.")
            return redirect('items:item_list')

        # Check if this is the confirmation step with new status
        if 'new_status' in request.POST:
            from django.db import transaction
            from django.utils import timezone

            new_status = request.POST.get('new_status')

            # Validate status
            valid_statuses = [choice[0] for choice in Item.Status.choices]
            if new_status not in valid_statuses:
                messages.error(request, f"Invalid status selected: {new_status}")
                return redirect('items:item_list')

            with transaction.atomic():
                # Lock rows for update to prevent race conditions
                items = Item.objects.filter(pk__in=item_ids).select_for_update()
                count = items.count()

                # Update status for all selected items
                items.update(status=new_status, updated_at=timezone.now())

            status_display = dict(Item.Status.choices).get(new_status, new_status)
            messages.success(
                request,
                f"{count} item(s) status changed to '{status_display}'."
            )
            return redirect('items:item_list')

        # Show status selection form
        items = Item.objects.filter(pk__in=item_ids)

        context = {
            'items': items,
            'item_ids': item_ids,
            'status_choices': Item.Status.choices,
        }

        return render(request, 'items/bulk_status_form.html', context)

    return redirect('items:item_list')


@staff_required
def bulk_transfer_items(request):
    """Transfer multiple items to a new owner at once (Staff/Admin only)."""
    from users.models import User
    from transfers.models import TransferLog

    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids')

        if not item_ids:
            messages.error(request, "No items selected for transfer.")
            return redirect('items:item_list')

        # Check if this is the confirmation step with new owner
        if 'new_owner' in request.POST:
            from django.db import transaction

            new_owner_id = request.POST.get('new_owner')
            notes = request.POST.get('notes', '')

            # Validate user exists and is active
            try:
                new_owner = User.objects.get(
                    pk=new_owner_id,
                    is_active=True,
                    role__in=['STAFF', 'MANAGER', 'TEACHER']
                )
            except User.DoesNotExist:
                messages.error(request, "Selected user does not exist or is not active.")
                return redirect('items:item_list')

            with transaction.atomic():
                # Lock items for update to prevent race conditions
                items = Item.objects.filter(pk__in=item_ids).select_for_update()
                count = 0

                # Transfer each item and create transfer log
                for item in items:
                    old_owner = item.current_owner
                    item.current_owner = new_owner
                    item.save()

                    # Create transfer log
                    TransferLog.objects.create(
                        item=item,
                        from_user=old_owner,
                        to_user=new_owner,
                        is_forced=True,
                        notes=notes or f"Bulk transfer by {request.user.email}"
                    )
                    count += 1

            messages.success(
                request,
                f"{count} item(s) transferred to {new_owner.email}."
            )
            return redirect('items:item_list')

        # Show owner selection form
        items = Item.objects.filter(pk__in=item_ids)
        users = User.objects.filter(is_active=True).order_by('email')

        context = {
            'items': items,
            'item_ids': item_ids,
            'users': users,
        }

        return render(request, 'items/bulk_transfer_form.html', context)

    return redirect('items:item_list')


@staff_required
def removed_items_list(request):
    """List all removed items (Staff/Admin only)."""
    items = Item.objects.filter(status='REMOVED').select_related('category', 'current_owner')

    context = {
        'items': items,
    }

    return render(request, 'items/removed_items_list.html', context)


@staff_required
def restore_item(request, pk):
    """Restore a removed item back to active status (Staff/Admin only)."""
    item = get_object_or_404(Item, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('new_status')

        if not new_status:
            messages.error(request, "Please select a status to restore the item to.")
            return redirect('items:restore_item', pk=pk)

        # Update item status
        old_status = item.get_status_display()
        item.status = new_status
        item.save()

        messages.success(
            request,
            f"Item {item.asset_id} - {item.name} has been restored from REMOVED to {item.get_status_display()}."
        )
        return redirect('items:removed_items_list')

    # GET: Show confirmation page
    # Available status choices (excluding REMOVED)
    status_choices = [
        (value, label) for value, label in Item.Status.choices
        if value != 'REMOVED'
    ]

    context = {
        'item': item,
        'status_choices': status_choices,
    }

    return render(request, 'items/item_restore_confirm.html', context)


@staff_required
def bulk_restore_items(request):
    """Restore multiple removed items at once (Staff/Admin only)."""
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids')

        if not item_ids:
            messages.error(request, "No items selected for restore.")
            return redirect('items:removed_items_list')

        # Check if this is the confirmation step with new status
        if 'new_status' in request.POST:
            from django.db import transaction
            from django.utils import timezone

            new_status = request.POST.get('new_status')

            # Validate status (should not be REMOVED)
            valid_statuses = [choice[0] for choice in Item.Status.choices if choice[0] != 'REMOVED']
            if new_status not in valid_statuses:
                messages.error(request, f"Invalid status selected for restore: {new_status}")
                return redirect('items:removed_items_list')

            with transaction.atomic():
                # Lock rows for update to prevent race conditions
                items = Item.objects.filter(pk__in=item_ids, status='REMOVED').select_for_update()
                count = items.count()

                # Update status for all selected items
                items.update(status=new_status, updated_at=timezone.now())

            status_display = dict(Item.Status.choices).get(new_status, new_status)
            messages.success(
                request,
                f"{count} item(s) restored to '{status_display}' status."
            )
            return redirect('items:removed_items_list')

        # Show status selection form
        items = Item.objects.filter(pk__in=item_ids)

        # Available status choices (excluding REMOVED)
        status_choices = [
            (value, label) for value, label in Item.Status.choices
            if value != 'REMOVED'
        ]

        context = {
            'items': items,
            'item_ids': item_ids,
            'status_choices': status_choices,
        }

        return render(request, 'items/bulk_restore_form.html', context)

    return redirect('items:removed_items_list')
