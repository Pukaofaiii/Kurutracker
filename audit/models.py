from django.db import models
from django.conf import settings


class AuditorAssignment(models.Model):
    """
    Assigns auditors to specific locations or departments.
    Controls which items an auditor can audit based on location/department.
    """

    auditor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auditor_assignments',
        limit_choices_to={'is_auditor': True},
        verbose_name='Auditor'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='auditor_assignments',
        verbose_name='Location'
    )
    department = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Department',
        help_text='Leave blank for all departments'
    )
    is_global = models.BooleanField(
        default=False,
        verbose_name='Global Access',
        help_text='Auditor can audit ALL items regardless of location/department'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Auditor Assignment'
        verbose_name_plural = 'Auditor Assignments'
        ordering = ['auditor', '-created_at']
        indexes = [
            models.Index(fields=['auditor']),
            models.Index(fields=['location']),
            models.Index(fields=['is_global']),
        ]
        # Prevent duplicate assignments for same auditor+location or auditor+department
        constraints = [
            models.UniqueConstraint(
                fields=['auditor', 'location'],
                condition=models.Q(location__isnull=False),
                name='unique_auditor_location'
            ),
            models.UniqueConstraint(
                fields=['auditor', 'department'],
                condition=models.Q(department__isnull=False),
                name='unique_auditor_department'
            ),
        ]

    def __str__(self):
        if self.is_global:
            return f"{self.auditor.email} - Global Access"
        elif self.location:
            return f"{self.auditor.email} - {self.location}"
        elif self.department:
            return f"{self.auditor.email} - {self.department}"
        return f"{self.auditor.email} - Assignment"

    def clean(self):
        """Validate that either location, department, or is_global is set."""
        from django.core.exceptions import ValidationError

        if not self.is_global and not self.location and not self.department:
            raise ValidationError(
                "Must specify either location, department, or set as global access."
            )

        if self.is_global and (self.location or self.department):
            raise ValidationError(
                "Global access cannot be combined with specific location or department."
            )
