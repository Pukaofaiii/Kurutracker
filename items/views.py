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
            return redirect('items:item_detail', pk=item.pk)
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
            return redirect('items:item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)

    context = {
        'form': form,
        'item': item,
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
                return redirect('items:item_detail', pk=pk)

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
        return redirect('items:item_detail', pk=pk)

    if request.method == 'POST':
        form = UpdateLocationForm(request.POST)
        if form.is_valid():
            item.current_location = form.cleaned_data['current_location']
            item.save()
            messages.success(
                request,
                f"Location updated for {item.asset_id} - {item.name}."
            )
            return redirect('items:item_detail', pk=pk)
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
