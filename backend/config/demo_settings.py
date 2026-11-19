"""Demostración local explícita. No acredita despliegue PostgreSQL."""
import os
os.environ.setdefault('DJANGO_SECRET_KEY', 'solo-demo-local-farmacia-no-usar-en-un-servidor-publico')
from .settings import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'demo.sqlite3'}}
SESSION_COOKIE_NAME = 'farmacia_ampliada_session'
CSRF_COOKIE_NAME = 'farmacia_ampliada_csrf'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = BASE_DIR / 'work' / 'correos'
