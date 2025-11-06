# Generated migration to rename TEACHER role to MEMBER role

from django.db import migrations, models


def rename_teacher_to_member(apps, schema_editor):
    """Rename all users with TEACHER role to MEMBER role."""
    User = apps.get_model('users', 'User')
    User.objects.filter(role='TEACHER').update(role='MEMBER')


def rename_member_to_teacher(apps, schema_editor):
    """Reverse migration: Rename MEMBER back to TEACHER."""
    User = apps.get_model('users', 'User')
    User.objects.filter(role='MEMBER').update(role='TEACHER')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_disable_expiration_emails'),
    ]

    operations = [
        # First update the existing data
        migrations.RunPython(
            rename_teacher_to_member,
            reverse_code=rename_member_to_teacher
        ),
        # Then alter the model field choices
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('MEMBER', 'Member'),
                    ('STAFF', 'Staff'),
                    ('MANAGER', 'Manager')
                ],
                default='MEMBER',
                max_length=10,
                verbose_name='User Role'
            ),
        ),
    ]
