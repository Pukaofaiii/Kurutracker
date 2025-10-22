"""
Forms for transfer workflow.
"""

from django import forms
from .models import TransferRequest
from items.models import Item
from users.models import User
from locations.models import Location


class TransferRequestForm(forms.ModelForm):
    """Form for creating a transfer request (Staff → Teacher)."""

    class Meta:
        model = TransferRequest
        fields = ['item', 'to_user', 'notes']
        widgets = {
            'item': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'to_user': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Notes (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

        # Show all available items (Staff/Manager can assign any item to teachers)
        if self.request_user:
            self.fields['item'].queryset = Item.objects.filter(
                status__in=['NORMAL', 'DAMAGED']
            ).select_related('current_owner', 'category')

        # Show both teachers and staff for transfer
        self.fields['to_user'].queryset = User.objects.filter(
            role__in=['TEACHER', 'STAFF'],
            is_active=True
        )


class ReturnRequestForm(forms.Form):
    """Form for creating a return request (Teacher → Staff)."""

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'Condition notes or reason for return (optional)'
        }),
        label='Notes'
    )


class AcceptTransferForm(forms.Form):
    """Form for accepting a transfer (ASSIGN) with required current_location."""

    current_location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='Current Location',
        help_text='Where will you keep this item? (Required)',
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom label for location dropdown
        self.fields['current_location'].label_from_instance = lambda obj: f"{obj.building} - Floor {obj.floor} - Room {obj.room}"


class AcceptReturnForm(forms.Form):
    """Form for accepting a return with status selection."""

    new_status = forms.ChoiceField(
        choices=Item.Status.choices,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='New Item Status',
        help_text='Select the status of the item after inspection'
    )


class RejectRequestForm(forms.Form):
    """Form for rejecting a transfer request."""

    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500',
            'rows': 3,
            'placeholder': 'Reason for rejection'
        }),
        label='Reason for Rejection'
    )
