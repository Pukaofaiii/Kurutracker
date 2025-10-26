"""
Django management command to manually trigger expiration check.

Usage:
    python manage.py expire_requests              # Run expiration check
    python manage.py expire_requests --dry-run    # Preview without making changes
    python manage.py expire_requests --verbose    # Show detailed output
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from transfers.models import TransferRequest
from transfers.tasks import check_expiring_requests
from notifications.utils import notify_request_expiring_soon, notify_request_expired


class Command(BaseCommand):
    help = 'Manually trigger expiration check for transfer requests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be done without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each request processed',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.stdout.write('')

        now = timezone.now()

        # Get all pending requests
        pending_requests = TransferRequest.objects.filter(
            status=TransferRequest.Status.PENDING
        ).select_related('item', 'to_user', 'from_user')

        if not pending_requests.exists():
            self.stdout.write(self.style.SUCCESS('No pending requests found.'))
            return

        self.stdout.write(f'Found {pending_requests.count()} pending requests')
        self.stdout.write('')

        stats = {
            'warnings_48h': 0,
            'warnings_24h': 0,
            'expired': 0,
            'pending': 0
        }

        for request in pending_requests:
            # Determine effective deadline (extended or original)
            deadline = request.expiration_extended_until or request.expires_at

            if not deadline:
                if verbose:
                    self.stdout.write(
                        f'  Request {request.pk}: No expiration date set'
                    )
                stats['pending'] += 1
                continue

            time_until_expiry = deadline - now
            hours_remaining = time_until_expiry.total_seconds() / 3600
            days_remaining = time_until_expiry.days

            # Expired
            if hours_remaining <= 0:
                stats['expired'] += 1
                if dry_run:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  [WOULD EXPIRE] Request {request.pk}: '
                            f'{request.item.asset_id} (expired {abs(days_remaining)} days ago)'
                        )
                    )
                else:
                    if verbose:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  [EXPIRING] Request {request.pk}: '
                                f'{request.item.asset_id}'
                            )
                        )
                    # Actually expire the request
                    from transfers.tasks import _expire_request
                    _expire_request(request)

            # 24-hour warning
            elif 24 <= hours_remaining < 25 and not request.warning_24h_sent:
                stats['warnings_24h'] += 1
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [WOULD SEND 24h WARNING] Request {request.pk}: '
                            f'{request.item.asset_id} (expires in {hours_remaining:.1f} hours)'
                        )
                    )
                else:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [SENDING 24h WARNING] Request {request.pk}: '
                                f'{request.item.asset_id}'
                            )
                        )
                    notify_request_expiring_soon(request, hours_remaining=24)
                    request.warning_24h_sent = True
                    request.save(update_fields=['warning_24h_sent', 'updated_at'])

            # 48-hour warning
            elif 48 <= hours_remaining < 49 and not request.warning_48h_sent:
                stats['warnings_48h'] += 1
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [WOULD SEND 48h WARNING] Request {request.pk}: '
                            f'{request.item.asset_id} (expires in {hours_remaining:.1f} hours)'
                        )
                    )
                else:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [SENDING 48h WARNING] Request {request.pk}: '
                                f'{request.item.asset_id}'
                            )
                        )
                    notify_request_expiring_soon(request, hours_remaining=48)
                    request.warning_48h_sent = True
                    request.save(update_fields=['warning_48h_sent', 'updated_at'])

            # Still pending
            else:
                stats['pending'] += 1
                if verbose:
                    self.stdout.write(
                        f'  Request {request.pk}: '
                        f'{request.item.asset_id} - '
                        f'{days_remaining} days remaining'
                    )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(f'  48-hour warnings: {stats["warnings_48h"]}')
        self.stdout.write(f'  24-hour warnings: {stats["warnings_24h"]}')
        self.stdout.write(f'  Expired: {stats["expired"]}')
        self.stdout.write(f'  Still pending: {stats["pending"]}')
        self.stdout.write(self.style.SUCCESS('=' * 60))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('✓ Expiration check complete'))
        else:
            self.stdout.write(
                self.style.WARNING('DRY RUN COMPLETE - Run without --dry-run to apply changes')
            )
