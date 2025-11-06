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


@manager_required
def room_import_csv(request):
    """Import rooms from CSV file."""
    import csv
    import io
    from .forms import RoomCSVImportForm

    if request.method == 'POST':
        form = RoomCSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            skip_duplicates = form.cleaned_data['skip_duplicates']

            # Validate file type
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'File must be a CSV file (.csv extension)')
                return redirect('locations:room_import')

            # Read CSV file
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)

                created_count = 0
                skipped_count = 0
                updated_count = 0
                errors = []

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        code = row.get('code', '').strip()
                        description = row.get('description', '').strip()
                        is_active_str = row.get('is_active', 'True').strip()

                        # Validate required field
                        if not code:
                            errors.append(f"Row {row_num}: Missing required field 'code'")
                            continue

                        # Parse is_active
                        is_active = is_active_str.lower() in ('true', '1', 'yes', 'y')

                        # Check if room exists
                        existing_room = Room.objects.filter(code=code).first()

                        if existing_room:
                            if skip_duplicates:
                                skipped_count += 1
                                continue
                            else:
                                # Update existing room
                                existing_room.description = description if description else None
                                existing_room.is_active = is_active
                                existing_room.save()
                                updated_count += 1
                        else:
                            # Create new room
                            Room.objects.create(
                                code=code,
                                description=description if description else None,
                                is_active=is_active
                            )
                            created_count += 1

                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")

                # Show results
                if errors:
                    for error in errors:
                        messages.warning(request, error)

                success_message = f"Import completed: {created_count} created"
                if updated_count > 0:
                    success_message += f", {updated_count} updated"
                if skipped_count > 0:
                    success_message += f", {skipped_count} skipped"

                messages.success(request, success_message)
                return redirect('locations:room_list')

            except Exception as e:
                messages.error(request, f"Error reading CSV file: {str(e)}")
    else:
        form = RoomCSVImportForm()

    context = {
        'form': form,
        'sample_csv': 'code,description,is_active\nsc201,Science Lab 201,True\nsc202,Science Lab 202,True\nlib101,Main Library,True'
    }
    return render(request, 'locations/room_import.html', context)
