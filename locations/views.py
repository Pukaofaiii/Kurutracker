"""
Location and room management views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from users.decorators import manager_required
from .models import Room, Location
from .forms import RoomForm, LocationForm


@manager_required
def room_list(request):
    """List all rooms with search and filtering."""
    search_query = request.GET.get('search', '')

    rooms = Room.objects.all()

    if search_query:
        rooms = rooms.filter(
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Get statistics
    total_rooms = Room.objects.count()
    active_rooms = Room.objects.filter(is_active=True).count()
    inactive_rooms = Room.objects.filter(is_active=False).count()

    # Annotate with item count
    rooms = rooms.annotate(item_count=Count('items')).order_by('code')

    context = {
        'rooms': rooms,
        'search_query': search_query,
        'total_rooms': total_rooms,
        'active_rooms': active_rooms,
        'inactive_rooms': inactive_rooms,
    }
    return render(request, 'locations/room_list.html', context)


@manager_required
def room_create(request):
    """Create a new room."""
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save()
            messages.success(request, f'Room "{room.code}" created successfully!')
            return redirect('locations:room_list')
    else:
        form = RoomForm()

    context = {'form': form, 'action': 'Create'}
    return render(request, 'locations/room_form.html', context)


@manager_required
def room_edit(request, pk):
    """Edit an existing room."""
    room = get_object_or_404(Room, pk=pk)

    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            room = form.save()
            messages.success(request, f'Room "{room.code}" updated successfully!')
            return redirect('locations:room_list')
    else:
        form = RoomForm(instance=room)

    context = {'form': form, 'room': room, 'action': 'Edit'}
    return render(request, 'locations/room_form.html', context)


@manager_required
def room_delete(request, pk):
    """Soft delete (deactivate) or permanently delete a room (Manager only for hard delete)."""
    room = get_object_or_404(Room, pk=pk)

    # Check if room has items
    item_count = room.items.exclude(status='REMOVED').count()

    if request.method == 'POST':
        room_code = room.code
        delete_type = request.POST.get('delete_type', 'soft')

        # Rooms with active items cannot be deleted (soft or hard)
        if item_count > 0:
            messages.error(
                request,
                f'Cannot delete room "{room_code}" because it has {item_count} active items assigned to it. '
                f'Please reassign items first.'
            )
            return redirect('locations:room_list')

        # Check if hard delete is requested
        if delete_type == 'hard':
            # Hard delete: Permanently remove from database
            room.delete()
            messages.success(
                request,
                f'Room "{room_code}" has been permanently deleted from the database.'
            )
        else:
            # Soft delete: Mark as inactive
            room.is_active = False
            room.save()
            messages.success(request, f'Room "{room_code}" deactivated successfully!')

        return redirect('locations:room_list')

    context = {'room': room, 'item_count': item_count}
    return render(request, 'locations/room_delete_confirm.html', context)


@manager_required
def room_activate(request, pk):
    """Reactivate a deactivated room."""
    room = get_object_or_404(Room, pk=pk)

    if request.method == 'POST':
        room.is_active = True
        room.save()
        messages.success(request, f'Room "{room.code}" activated successfully!')
        return redirect('locations:room_list')

    context = {'room': room}
    return render(request, 'locations/room_activate_confirm.html', context)
