"""
User management views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q

from .models import User
from .forms import UserPreRegisterForm, UserEditForm, ForcedTransferForm
from .decorators import staff_required, manager_required
from items.models import Item
from transfers.models import TransferLog


@manager_required
def user_list(request):
    """List all users (Manager only)."""
    users = User.objects.all().annotate(
        item_count=Count('current_items', filter=Q(current_items__status__in=['NORMAL', 'DAMAGED', 'PENDING_INSPECTION']))
    ).order_by('-created_at')

    # Filter by role if specified
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)

    # Filter by active status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    # Calculate statistics
    users_list = list(users)  # Convert to list to avoid multiple queries
    total_users = len(users_list)
    active_users = sum(1 for user in users_list if user.is_active)
    manager_count = sum(1 for user in users_list if user.is_manager)
    inactive_users = total_users - active_users

    context = {
        'users': users_list,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'total_users': total_users,
        'active_users': active_users,
        'manager_count': manager_count,
        'inactive_users': inactive_users,
    }

    return render(request, 'users/user_list.html', context)


@manager_required
def user_pre_register(request):
    """Pre-register a new user (Manager only)."""
    generated_password = None

    if request.method == 'POST':
        form = UserPreRegisterForm(request.POST, request_user=request.user)
        if form.is_valid():
            user, generated_password = form.save()
            messages.success(
                request,
                f"User {user.email} has been created successfully. "
                f"They can login with Google OAuth OR with the generated password below."
            )
            # Store password in session to display once
            request.session['generated_password'] = generated_password
            request.session['generated_for_email'] = user.email
            return redirect('users:user_pre_register')
    else:
        form = UserPreRegisterForm(request_user=request.user)

        # Check if there's a generated password to display
        if 'generated_password' in request.session:
            generated_password = request.session.pop('generated_password')
            generated_for_email = request.session.pop('generated_for_email', '')
            messages.warning(
                request,
                f"⚠️ IMPORTANT: Save this password now! It will only be shown once for {generated_for_email}"
            )

    context = {
        'form': form,
        'generated_password': generated_password,
    }

    return render(request, 'users/user_pre_register.html', context)


@manager_required
def user_detail(request, pk):
    """View user details (Manager only)."""
    user = get_object_or_404(User, pk=pk)

    # Get user's items
    items = Item.objects.filter(current_owner=user)

    # Get transfer history (sent and received)
    transfers_sent = TransferLog.objects.filter(from_user=user).order_by('-transferred_at')[:20]
    transfers_received = TransferLog.objects.filter(to_user=user).order_by('-transferred_at')[:20]

    context = {
        'user_obj': user,  # Use user_obj to avoid conflict with request.user
        'items': items,
        'items_count': items.count(),
        'transfers_sent': transfers_sent,
        'transfers_received': transfers_received,
    }

    return render(request, 'users/user_detail.html', context)


@manager_required
def user_edit(request, pk):
    """Edit user details (Manager only)."""
    user = get_object_or_404(User, pk=pk)
    generated_password = None

    # Prevent editing yourself
    if user == request.user:
        messages.error(request, "You cannot edit your own account. Please ask another manager.")
        return redirect('users:user_list')

    # Prevent editing other managers unless you're a superuser
    if user.role == 'MANAGER' and not request.user.is_superuser:
        messages.error(request, "Only superusers can edit manager accounts.")
        return redirect('users:user_list')

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user, request_user=request.user)
        if form.is_valid():
            user, generated_password = form.save()

            if generated_password:
                messages.success(
                    request,
                    f"User {user.email} updated successfully with new password!"
                )
                # Store password in session to display once
                request.session['generated_password'] = generated_password
                request.session['generated_for_email'] = user.email
                return redirect('users:user_edit', pk=pk)
            else:
                messages.success(request, f"User {user.email} updated successfully.")
                return redirect('users:user_edit', pk=pk)
    else:
        form = UserEditForm(instance=user, request_user=request.user)

        # Check if there's a generated password to display
        if 'generated_password' in request.session:
            generated_password = request.session.pop('generated_password')
            generated_for_email = request.session.pop('generated_for_email', '')
            messages.warning(
                request,
                f"⚠️ IMPORTANT: Save this password now! It will only be shown once for {generated_for_email}"
            )

    context = {
        'form': form,
        'user_obj': user,
        'generated_password': generated_password,
    }

    return render(request, 'users/user_edit.html', context)


@manager_required
def user_deactivate(request, pk):
    """Deactivate a user (Manager only)."""
    user = get_object_or_404(User, pk=pk)

    # Prevent deactivating yourself
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('users:user_edit', pk=pk)

    # Check if user has items
    item_count = user.get_item_count()

    if request.method == 'POST':
        if item_count > 0:
            messages.error(
                request,
                f"Cannot deactivate {user.email}. User still holds {item_count} items. "
                f"Please use Forced Transfer or manually transfer all items first."
            )
            return redirect('users:user_edit', pk=pk)

        try:
            user.deactivate()
            messages.success(
                request,
                f"User {user.email} has been deactivated successfully."
            )
            return redirect('users:user_list')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('users:user_edit', pk=pk)

    context = {
        'user_obj': user,
        'item_count': item_count,
    }

    return render(request, 'users/user_deactivate_confirm.html', context)


@manager_required
def user_forced_transfer(request, pk):
    """
    Force transfer all items from a user to a staff member (Manager only).
    Used for emergency situations like employee resignation.
    """
    source_user = get_object_or_404(User, pk=pk)

    # Get items held by user (initial count check)
    items_preview = Item.objects.filter(
        current_owner=source_user,
        status__in=['NORMAL', 'DAMAGED', 'PENDING_INSPECTION']
    )
    item_count_preview = items_preview.count()

    if item_count_preview == 0:
        messages.info(request, f"{source_user.email} does not hold any items.")
        return redirect('users:user_edit', pk=pk)

    if request.method == 'POST':
        form = ForcedTransferForm(request.POST)
        if form.is_valid():
            target_staff = form.cleaned_data['target_staff']

            try:
                with transaction.atomic():
                    # Lock items for update to prevent race conditions
                    items = Item.objects.filter(
                        current_owner=source_user,
                        status__in=['NORMAL', 'DAMAGED', 'PENDING_INSPECTION']
                    ).select_for_update()

                    item_count = items.count()

                    # Transfer all items
                    for item in items:
                        old_owner = item.current_owner
                        item.current_owner = target_staff
                        item.save()

                        # Create transfer log with is_forced=True
                        TransferLog.objects.create(
                            item=item,
                            from_user=old_owner,
                            to_user=target_staff,
                            request=None,  # No request for forced transfers
                            notes=f"Forced transfer by Admin {request.user.email}",
                            is_forced=True
                        )

                    messages.success(
                        request,
                        f"Successfully transferred {item_count} items from {source_user.email} "
                        f"to {target_staff.email}. You can now deactivate the user if needed."
                    )
                    return redirect('users:user_edit', pk=pk)

            except Exception as e:
                messages.error(request, f"Error during forced transfer: {str(e)}")
                return redirect('users:user_forced_transfer', pk=pk)
    else:
        form = ForcedTransferForm()

    context = {
        'source_user': source_user,
        'items': items_preview,
        'item_count': item_count_preview,
        'form': form,
    }

    return render(request, 'users/user_forced_transfer.html', context)


@manager_required
def user_activate(request, pk):
    """Reactivate a deactivated user (Manager only)."""
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        user.is_active = True
        user.save()
        messages.success(
            request,
            f"User {user.email} has been reactivated successfully."
        )
        return redirect('users:user_edit', pk=pk)

    context = {
        'user_obj': user,
    }

    return render(request, 'users/user_activate_confirm.html', context)


@manager_required
def grant_auditor_permission(request, pk):
    """Grant auditor permission to a user (Manager only)."""
    user = get_object_or_404(User, pk=pk)

    # Prevent granting to yourself (optional - managers might want to make themselves auditors)
    # if user == request.user:
    #     messages.error(request, "You cannot modify your own auditor permission.")
    #     return redirect('users:user_detail', pk=pk)

    if user.is_auditor:
        messages.info(request, f"{user.email} already has auditor permission.")
        return redirect('users:user_edit', pk=pk)

    if request.method == 'POST':
        user.is_auditor = True
        user.save()
        messages.success(
            request,
            f"Auditor permission granted to {user.email}. They can now access the audit checklist."
        )
        return redirect('users:user_edit', pk=pk)

    context = {
        'user_obj': user,
    }

    return render(request, 'users/grant_auditor_confirm.html', context)


@manager_required
def revoke_auditor_permission(request, pk):
    """Revoke auditor permission from a user (Manager only)."""
    user = get_object_or_404(User, pk=pk)

    if not user.is_auditor:
        messages.info(request, f"{user.email} does not have auditor permission.")
        return redirect('users:user_edit', pk=pk)

    if request.method == 'POST':
        user.is_auditor = False
        user.save()
        messages.success(
            request,
            f"Auditor permission revoked from {user.email}."
        )
        return redirect('users:user_edit', pk=pk)

    context = {
        'user_obj': user,
    }

    return render(request, 'users/revoke_auditor_confirm.html', context)
