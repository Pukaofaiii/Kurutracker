"""
Decorators for audit permissions.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def auditor_required(view_func):
    """
    Decorator for views that require auditor permission.
    Allows users with is_auditor=True, staff, or managers.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('account_login')

        # Allow auditors, staff, or managers
        if request.user.is_auditor or request.user.is_staff_or_manager:
            return view_func(request, *args, **kwargs)

        messages.error(request, 'You need auditor permission to access this page.')
        return redirect('core:dashboard')

    return wrapper


def auditor_or_manager_required(view_func):
    """
    Decorator for views that require auditor permission or manager role.
    Used for sensitive audit functions like reports.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('account_login')

        # Allow auditors or managers
        if request.user.is_auditor or request.user.is_manager:
            return view_func(request, *args, **kwargs)

        messages.error(request, 'You need auditor permission or manager role to access this page.')
        return redirect('core:dashboard')

    return wrapper
