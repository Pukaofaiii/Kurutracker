"""
Forms for user management.
"""

import secrets
import string
from django import forms
from django.core.exceptions import ValidationError
from .models import User


class UserPreRegisterForm(forms.ModelForm):
    """Form for pre-registering a new user."""

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'role', 'department', 'phone_number']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'member@school.ac.th'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Last Name'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            'department': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Department (optional)'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Phone Number (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

        # Staff can only add Members
        if self.request_user and self.request_user.role == 'STAFF':
            self.fields['role'].choices = [('MEMBER', 'Member')]

    def clean_email(self):
        """Validate email is not already registered."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(f"User with email {email} already exists.")
        return email

    @staticmethod
    def generate_password(length=12):
        """
        Generate a secure random password.
        Returns password with: uppercase, lowercase, digits, and special characters.
        """
        alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%&*"

        # Ensure at least one character from each category
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%&*")
        ]

        # Fill the rest randomly
        for _ in range(length - 4):
            password.append(secrets.choice(alphabet))

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)

    def save(self, commit=True):
        """
        Save user with generated password.
        Returns tuple: (user, generated_password)
        """
        user = super().save(commit=False)
        user.is_pre_registered = True

        # Generate secure password
        password = self.generate_password()
        user.set_password(password)

        if commit:
            user.save()

        return user, password  # Return both user and password for display


class UserEditForm(forms.ModelForm):
    """Form for editing existing user."""

    reset_password = forms.BooleanField(
        required=False,
        label='Reset Password',
        help_text='Check this box to generate a new password for the user',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'role', 'department', 'phone_number', 'is_auditor', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'readonly': 'readonly'  # Email shouldn't be changed
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'department': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'is_auditor': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-yellow-600 border-gray-300 rounded focus:ring-yellow-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

        # Only managers can edit roles and auditor permission
        if self.request_user and self.request_user.role != 'MANAGER':
            self.fields['role'].disabled = True
            self.fields['role'].help_text = 'Only managers can change user roles'
            self.fields['is_auditor'].disabled = True
            self.fields['is_auditor'].help_text = 'Only managers can grant auditor permission'

        # Staff can't edit manager accounts
        if self.request_user and self.request_user.role == 'STAFF':
            if self.instance.role == 'MANAGER':
                for field in self.fields:
                    self.fields[field].disabled = True

    def save(self, commit=True):
        """
        Save user with optional password reset.
        Returns tuple: (user, generated_password or None)
        """
        user = super().save(commit=False)
        generated_password = None

        # Generate new password if requested
        if self.cleaned_data.get('reset_password'):
            generated_password = UserPreRegisterForm.generate_password()
            user.set_password(generated_password)

        if commit:
            user.save()

        return user, generated_password


class ForcedTransferForm(forms.Form):
    """Form for forced transfer of all items from one user to another."""

    target_staff = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=['STAFF', 'MANAGER'], is_active=True),
        label='Transfer all items to:',
        help_text='Select a Staff or Manager user to receive all items.',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-4 focus:ring-orange-100 focus:outline-none transition-all'
        })
    )

    confirm = forms.BooleanField(
        required=True,
        label='I understand this action cannot be undone',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500'
        })
    )
