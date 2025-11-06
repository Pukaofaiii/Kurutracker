"""
Django-allauth adapters for custom authentication logic.
Prevents unauthorized signups - only pre-registered users can login.
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from .models import User


class NoSignupAccountAdapter(DefaultAccountAdapter):
    """
    Adapter for account signup with custom logic.
    New users are created with MEMBER role by default.
    """

    def is_open_for_signup(self, request):
        """
        Allow public signup.
        New users will be created with MEMBER role.
        """
        return True

    def save_user(self, request, user, form, commit=True):
        """
        Custom user save logic - creates new users with MEMBER role.
        """
        user = super().save_user(request, user, form, commit=False)

        # Set default role to MEMBER for new signups
        user.role = 'MEMBER'
        user.is_pre_registered = True  # Mark as registered since they just signed up

        if commit:
            user.save()

        return user


class PreRegisteredSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter for OAuth login.
    Allows signup via OAuth - new users created with MEMBER role.
    """

    def is_open_for_signup(self, request, sociallogin):
        """
        Allow OAuth signup for all users.
        New OAuth users will be created with MEMBER role.
        """
        email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None

        if not email:
            return False

        # Allow all OAuth signups
        return True

    def pre_social_login(self, request, sociallogin):
        """
        Invoked before social login. Check if user is active.
        """
        email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None

        if not email:
            messages.error(
                request,
                "Unable to retrieve email from your account. Please try again."
            )
            return redirect('account_login')

        # Check if existing user is active
        try:
            user = User.objects.get(email=email)

            if not user.is_active:
                messages.error(
                    request,
                    f"Your account ({email}) has been deactivated. "
                    f"Please contact your administrator."
                )
                sociallogin.disconnect(request)
                return redirect('account_login')

        except User.DoesNotExist:
            # New user - will be created with MEMBER role
            pass

    def populate_user(self, request, sociallogin, data):
        """
        Populate user instance with data from social provider.
        """
        user = super().populate_user(request, sociallogin, data)

        # Get existing user from database
        email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None
        if email:
            try:
                existing_user = User.objects.get(email=email)
                # Update user info from OAuth (name, etc.)
                user.first_name = data.get('first_name', existing_user.first_name)
                user.last_name = data.get('last_name', existing_user.last_name)
                user.role = existing_user.role  # Preserve existing role
                user.is_pre_registered = True
            except User.DoesNotExist:
                # New OAuth user - set MEMBER role by default
                user.role = 'MEMBER'
                user.is_pre_registered = True

        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Save the social account user.
        Updates existing users or creates new ones with MEMBER role.
        """
        email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None

        if email:
            try:
                # Get existing user
                user = User.objects.get(email=email)

                # Update user info from OAuth
                if sociallogin.account.extra_data:
                    user.first_name = sociallogin.account.extra_data.get(
                        'given_name',
                        user.first_name
                    )
                    user.last_name = sociallogin.account.extra_data.get(
                        'family_name',
                        user.last_name
                    )

                user.save()
                return user

            except User.DoesNotExist:
                # Create new OAuth user with MEMBER role
                user = super().save_user(request, sociallogin, form)
                user.role = 'MEMBER'
                user.is_pre_registered = True
                user.save()
                return user

        # Fallback to default behavior
        return super().save_user(request, sociallogin, form)
