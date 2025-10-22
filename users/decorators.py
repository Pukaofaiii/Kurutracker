"""
Custom decorators for role-based access control.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def role_required(allowed_roles):
    """
    Decorator to restrict access to views based on user roles.

    Usage:
        @role_required(['STAFF', 'MANAGER'])
        def my_view(request):
            ...

    Args:
        allowed_roles: List of role strings (e.g., ['TEACHER', 'STAFF', 'MANAGER'])
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(
                    request,
                    f"Access denied. This page requires {' or '.join(allowed_roles)} role."
                )
                raise PermissionDenied
        return wrapper
    return decorator


def staff_required(view_func):
    """Shortcut decorator for Staff-only views."""
    return role_required(['STAFF', 'MANAGER'])(view_func)


def manager_required(view_func):
    """Shortcut decorator for Manager-only views."""
    return role_required(['MANAGER'])(view_func)


def teacher_or_staff_required(view_func):
    """Shortcut decorator for Teacher/Staff/Manager views."""
    return role_required(['TEACHER', 'STAFF', 'MANAGER'])(view_func)


def check_user_can_manage_items(user):
    """Check if user can manage items (CRUD operations)."""
    return user.is_authenticated and user.can_manage_items()


def check_user_can_manage_users(user):
    """Check if user can manage other users."""
    return user.is_authenticated and user.can_manage_users()


def check_user_can_force_transfer(user):
    """Check if user can force transfer without approval."""
    return user.is_authenticated and user.can_force_transfer()


def owns_item_or_staff(view_func):
    """
    Decorator to check if user owns the item or is Staff/Admin.
    Expects 'item_id' or 'pk' in URL kwargs.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        from items.models import Item

        item_id = kwargs.get('pk') or kwargs.get('item_id')
        if not item_id:
            raise PermissionDenied("No item ID provided")

        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            raise PermissionDenied("Item not found")

        # Allow if user owns the item or is Staff/Admin
        if item.current_owner == request.user or request.user.can_manage_items():
            return view_func(request, *args, **kwargs)
        else:
            messages.error(
                request,
                "Access denied. You can only view items you own."
            )
            raise PermissionDenied

    return wrapper


def auditor_required(view_func):
    """
    Decorator to restrict access to views for users with auditor permission.

    Usage:
        @auditor_required
        def my_audit_view(request):
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_auditor:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(
                request,
                "Access denied. You must have auditor permission to access this page."
            )
            raise PermissionDenied
    return wrapper
