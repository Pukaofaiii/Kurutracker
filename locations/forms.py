"""
Forms for location and room management.
"""

from django import forms
from .models import Room, Location


class RoomForm(forms.ModelForm):
    """Form for creating/editing rooms."""

    class Meta:
        model = Room
        fields = ['code', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Room Code (e.g., sc201)'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Optional description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
        }


class LocationForm(forms.ModelForm):
    """Form for creating/editing locations."""

    class Meta:
        model = Location
        fields = ['building', 'floor', 'room', 'description', 'is_active']
        widgets = {
            'building': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Building name or number'
            }),
            'floor': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Floor number'
            }),
            'room': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Room number'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Additional location details (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500'
            }),
        }
