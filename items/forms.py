"""
Forms for item management.
"""

from django import forms
from .models import Item, ItemCategory
from locations.models import Location, Room


class ItemForm(forms.ModelForm):
    """Form for creating/editing items."""

    class Meta:
        model = Item
        fields = [
            'name', 'model', 'asset_id', 'category', 'description',
            'image', 'price', 'room', 'location_description', 'home_base_location',
            'current_owner', 'status', 'date_acquired'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Item Name'
            }),
            'model': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Model/Version (optional)'
            }),
            'asset_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Unique Asset ID'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Description (optional)'
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'room': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 room-autocomplete',
                'placeholder': 'Select room...',
                'data-autocomplete': 'true'
            }),
            'location_description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'e.g., Building 1, floor 2'
            }),
            'home_base_location': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'required': False
            }),
            'current_owner': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'date_acquired': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate location choices with active locations only
        self.fields['home_base_location'].queryset = Location.objects.filter(is_active=True)
        self.fields['home_base_location'].label_from_instance = lambda obj: f"{obj.building} - Floor {obj.floor} - Room {obj.room}"

        # Populate room choices with active rooms only
        self.fields['room'].queryset = Room.objects.filter(is_active=True)
        self.fields['room'].empty_label = "Select a room..."


class ItemFilterForm(forms.Form):
    """Form for filtering items list."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Search by name, asset ID, or model...'
        })
    )

    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Item.Status.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    owner = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from users.models import User
        # Populate owner choices dynamically
        owners = User.objects.filter(is_active=True).values_list('id', 'email')
        self.fields['owner'].choices = [('', 'All Owners')] + list(owners)


class CategoryForm(forms.ModelForm):
    """Form for creating/editing categories."""

    class Meta:
        model = ItemCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Category Name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Description (optional)'
            }),
        }


class UpdateLocationForm(forms.Form):
    """Form for item owners to update current_location."""

    current_location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='Current Location',
        help_text='Update where you are currently keeping this item',
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom label for location dropdown
        self.fields['current_location'].label_from_instance = lambda obj: f"{obj.building} - Floor {obj.floor} - Room {obj.room}"
