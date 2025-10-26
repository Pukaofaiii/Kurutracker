"""
Validators for user model fields.
"""

from django.core.validators import RegexValidator


# Phone number validator (International E.164 format)
# Accepts formats like: +999999999999, 0999999999, (999) 999-9999
phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)
