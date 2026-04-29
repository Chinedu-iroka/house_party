import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

app = Celery('houseparty')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat schedule
app.conf.beat_schedule = {
    'cleanup-expired-reservations': {
        'task': 'communications.tasks.cleanup_expired_reservations',
        'schedule': 60.0,  # runs every 60 seconds
    },
}

app.conf.timezone = 'Africa/Lagos'