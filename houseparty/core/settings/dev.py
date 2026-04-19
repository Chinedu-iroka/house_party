from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

handler404 = 'events.views.custom_404'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'