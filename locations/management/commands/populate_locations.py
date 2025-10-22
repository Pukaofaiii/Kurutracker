"""
Management command to populate initial location data.
Usage: python manage.py populate_locations
"""

from django.core.management.base import BaseCommand
from locations.models import Location


class Command(BaseCommand):
    help = 'Populate initial location data (buildings, floors, rooms)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating location data...')

        # Define buildings
        buildings = [
            {
                'name': 'Main Building',
                'floors': ['1', '2', '3'],
                'rooms_per_floor': list(range(201, 255))  # 201-254
            },
            {
                'name': 'Science Building',
                'floors': ['1', '2'],
                'rooms_per_floor': list(range(201, 230))  # 201-229
            },
            {
                'name': 'Administration Building',
                'floors': ['1', '2'],
                'rooms_per_floor': list(range(201, 220))  # 201-219
            },
        ]

        created_count = 0
        skipped_count = 0

        for building_data in buildings:
            building_name = building_data['name']

            for floor in building_data['floors']:
                # Create a few specific rooms for each floor
                # Room numbers like 201, 202, 203... up to 254
                for room_num in building_data['rooms_per_floor']:
                    room = str(room_num)

                    # Check if location already exists
                    if Location.objects.filter(
                        building=building_name,
                        floor=floor,
                        room=room
                    ).exists():
                        skipped_count += 1
                        continue

                    # Create location
                    Location.objects.create(
                        building=building_name,
                        floor=floor,
                        room=room,
                        description=f'Room {room} on Floor {floor} in {building_name}',
                        is_active=True
                    )
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} locations '
                f'(skipped {skipped_count} existing)'
            )
        )
