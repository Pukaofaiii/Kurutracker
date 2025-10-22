"""
Celery configuration for Kurutracker.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('kurutracker')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'expire-old-requests': {
        'task': 'transfers.tasks.expire_old_requests',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
    },
    'send-expiration-reminders': {
        'task': 'transfers.tasks.send_expiration_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
}

app.conf.timezone = 'Asia/Bangkok'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
