from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from .validators import phone_validator


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a manager user with Django admin access."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.MANAGER)
        extra_fields.setdefault('is_pre_registered', True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with role-based access control."""

    class Role(models.TextChoices):
        MEMBER = 'MEMBER', 'Member'
        STAFF = 'STAFF', 'Staff'
        MANAGER = 'MANAGER', 'Manager'

    # Remove username, use email instead
    username = None
    email = models.EmailField(unique=True, verbose_name='Email Address')

    # Additional fields
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name='User Role'
    )
    is_pre_registered = models.BooleanField(
        default=False,
        help_text='User must be pre-registered by Staff/Admin to login'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Phone Number',
        validators=[phone_validator]
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Department'
    )
    is_auditor = models.BooleanField(
        default=False,
        verbose_name='Auditor Permission',
        help_text='User can access audit checklist and mark items as damaged/lost'
    )
    disable_expiration_emails = models.BooleanField(
        default=False,
        verbose_name='Disable Expiration Warning Emails',
        help_text='Opt out of email notifications for expiring requests (web notifications will still be sent)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by USERNAME_FIELD

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_auditor']),
            models.Index(fields=['role', 'is_active']),  # Composite index for common queries
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split('@')[0]

    @property
    def is_member(self):
        """Check if user is a member."""
        return self.role == self.Role.MEMBER

    @property
    def is_staff_member(self):
        """Check if user is a staff member."""
        return self.role == self.Role.STAFF

    @property
    def is_manager(self):
        """Check if user is a manager."""
        return self.role == self.Role.MANAGER

    @property
    def is_admin(self):
        """Alias for is_manager (backwards compatibility)."""
        return self.is_manager

    @property
    def is_staff_or_admin(self):
        """Check if user is staff or manager."""
        return self.role in [self.Role.STAFF, self.Role.MANAGER]

    @property
    def is_staff_or_manager(self):
        """Check if user is staff or manager."""
        return self.role in [self.Role.STAFF, self.Role.MANAGER]

    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.role in [self.Role.STAFF, self.Role.MANAGER]

    def can_manage_items(self):
        """Check if user can manage items (CRUD operations)."""
        return self.role in [self.Role.STAFF, self.Role.MANAGER]

    def can_force_transfer(self):
        """Check if user can force transfer items without approval."""
        return self.role == self.Role.MANAGER

    def can_audit_item(self, item):
        """
        Check if user can audit a specific item.

        Staff and managers can audit any item.
        Auditors can only audit items they're assigned to via AuditorAssignment.

        Args:
            item: Item instance to check audit permission for

        Returns:
            bool: True if user can audit this item, False otherwise
        """
        # Staff and managers can audit any item
        if self.role in [self.Role.STAFF, self.Role.MANAGER]:
            return True

        # Non-auditors cannot audit
        if not self.is_auditor:
            return False

        # Import here to avoid circular import
        from audit.models import AuditorAssignment

        # Check for global auditor permission
        if AuditorAssignment.objects.filter(
            auditor=self,
            is_global=True
        ).exists():
            return True

        # Check location-based permission
        if item.current_location and AuditorAssignment.objects.filter(
            auditor=self,
            location=item.current_location
        ).exists():
            return True

        # Check department-based permission
        if item.current_owner and item.current_owner.department:
            if AuditorAssignment.objects.filter(
                auditor=self,
                department=item.current_owner.department
            ).exists():
                return True

        # No permission found
        return False

    def has_items(self):
        """Check if user currently holds any items."""
        return self.current_items.filter(
            status__in=['NORMAL', 'DAMAGED', 'PENDING_INSPECTION']
        ).exists()

    def get_item_count(self):
        """Get count of items currently held by user."""
        return self.current_items.filter(
            status__in=['NORMAL', 'DAMAGED', 'PENDING_INSPECTION']
        ).count()

    def delete(self, *args, **kwargs):
        """Override delete to prevent deletion of users with items."""
        if self.has_items():
            raise ValidationError(
                f"Cannot delete {self.email}. User still holds {self.get_item_count()} items. "
                f"Transfer all items first or use Forced Transfer."
            )
        super().delete(*args, **kwargs)

    def deactivate(self):
        """Deactivate user account (set is_active=False)."""
        if self.has_items():
            raise ValidationError(
                f"Cannot deactivate {self.email}. User still holds {self.get_item_count()} items. "
                f"Transfer all items first or use Forced Transfer."
            )
        self.is_active = False
        self.save()
