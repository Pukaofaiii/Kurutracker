"""
Management command to populate room codes sc201-sc254.
Run with: python manage.py populate_rooms
"""

from django.core.management.base import BaseCommand
from locations.models import Room


class Command(BaseCommand):
    help = 'Populate room codes sc201 through sc254'

    def handle(self, *args, **options):
        self.stdout.write('Populating rooms sc201 through sc254...')

        created_count = 0
        existing_count = 0

        for room_number in range(201, 255):  # 201-254 inclusive
            room_code = f'sc{room_number}'

            # Create room if it doesn't exist
            room, created = Room.objects.get_or_create(
                code=room_code,
                defaults={
                    'description': f'Science lab room {room_number}',
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created room: {room_code}')
                )
            else:
                existing_count += 1

        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'\nSummary:')
        )
        self.stdout.write(f'  - Created: {created_count} new rooms')
        self.stdout.write(f'  - Already existed: {existing_count} rooms')
        self.stdout.write(f'  - Total rooms: {Room.objects.count()}')
        self.stdout.write(self.style.SUCCESS('\n✓ Room population complete!'))
