import os

os.environ.setdefault('SECRET_KEY', 'dev-only-secret-key')
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1')
os.environ.setdefault('DB_NAME', 'club_db')
os.environ.setdefault('DB_USER', 'postgres')
os.environ.setdefault('DB_PASSWORD', 'postgres')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
CORS_ALLOW_ALL_ORIGINS = True

# Use real SMTP in development unless explicitly forced to console.
USE_CONSOLE_EMAIL = os.environ.get('USE_CONSOLE_EMAIL', '0') == '1'
if USE_CONSOLE_EMAIL:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    if not os.environ.get('DEFAULT_FROM_EMAIL') and os.environ.get('EMAIL_HOST_USER'):
        DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_HOST_USER')

# Optional: frontend club portal URL used in credential emails.
CLUB_PORTAL_URL = os.environ.get('CLUB_PORTAL_URL', 'http://127.0.0.1:8000/club/')

# Google OAuth for Calendar integration (set in environment or .env)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
# Redirect URI for the OAuth flow. Example: 'http://127.0.0.1:8000/api/v1/events/google/callback/'
GOOGLE_OAUTH_REDIRECT = os.environ.get('GOOGLE_OAUTH_REDIRECT')
