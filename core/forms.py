"""
Forms for core app - profile editing.
"""

from django import forms
from users.models import User


class ProfileEditForm(forms.ModelForm):
    """Form for users to edit their own profile information."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'department', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 focus:outline-none transition-all duration-300 text-gray-700 font-medium',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 focus:outline-none transition-all duration-300 text-gray-700 font-medium',
                'placeholder': 'Last Name'
            }),
            'department': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 focus:outline-none transition-all duration-300 text-gray-700 font-medium',
                'placeholder': 'Department (optional)'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 focus:outline-none transition-all duration-300 text-gray-700 font-medium',
                'placeholder': 'Phone Number (optional)'
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'department': 'Department',
            'phone_number': 'Phone Number',
        }
