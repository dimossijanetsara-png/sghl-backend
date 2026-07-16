from pathlib import Path
from datetime import timedelta
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,10.0.2.2').split(',')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'ninja',
    'corsheaders',
    'channels',
]

LOCAL_APPS = [
    'apps.core',
    'apps.authentication',
    'apps.patients',
    'apps.clinical',
    'apps.hospitalization',
    'apps.nursing',
    'apps.laboratory',
    'apps.pharmacy',
    'apps.billing',
    'apps.hr',
    'apps.appointments',
    'apps.messaging',
    'apps.dashboard',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.logging_config.RequestIdMiddleware',
    'apps.core.middleware.AuditMiddleware',
    'apps.core.middleware.RateLimitMiddleware',
    'apps.core.middleware.MetricsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Base de données : DATABASE_URL (Render) > SQLite dev > PostgreSQL manuel
_database_url = os.getenv('DATABASE_URL', '')
_use_sqlite = os.getenv('DB_USE_SQLITE', 'False') == 'True'

if _database_url:
    # Render fournit DATABASE_URL automatiquement
    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
elif _use_sqlite:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'sghl_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                'connect_timeout': 10,
                'client_encoding': 'UTF8',
            },
            'CONN_MAX_AGE': 60,
        }
    }

# Redis Cache — fallback vers LocMemCache si Redis non disponible (dev sans Redis)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
_use_redis = os.getenv('CACHE_USE_REDIS', 'False') == 'True'

if _use_redis:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'sghl-cache',
            'TIMEOUT': 300,
        }
    }

# Channel layers (WebSocket) — InMemoryChannelLayer si Redis absent
if _use_redis:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Brazzaville'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'authentication.User'

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Email — console fallback si les credentials Gmail ne sont pas configurés
_email_user = os.getenv('EMAIL_HOST_USER', '')
_email_pass = os.getenv('EMAIL_HOST_PASSWORD', '')
_placeholder = ('your-email@gmail.com', 'your-app-password', '')

if _email_user in _placeholder or _email_pass in _placeholder:
    # Dev sans SMTP : affiche l'OTP dans la console Django
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = _email_user
    EMAIL_HOST_PASSWORD = _email_pass
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'SGHL <{_email_user or "noreply@sghl.com"}>')

# CORS
_frontend_url = os.getenv('FRONTEND_URL', '')
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
    'http://localhost:62314',
    'http://127.0.0.1:62314',
    *([_frontend_url] if _frontend_url else []),
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^http://localhost:\d+$',
    r'^http://127\.0\.0\.1:\d+$',
    r'^http://10\.0\.2\.2:\d+$',  # Android emulator → host machine
    r'^https://[\w-]+\.onrender\.com$',  # tous les sous-domaines Render
]
CORS_ALLOW_CREDENTIALS = True

# Security
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# AES Encryption key
AES_ENCRYPTION_KEY = os.getenv('AES_ENCRYPTION_KEY', 'sghl-aes-256-key-change-in-prod!')

# File upload
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_UPLOAD_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/dicom']

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds

# Logging — filtre request_id uniquement en dev (évite l'erreur sur Render)
if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
        },
        'filters': {
            'request_id': {
                '()': 'apps.core.logging_config.RequestIdFilter',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                'filters': ['request_id'],
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'filters': ['request_id'],
        },
        'loggers': {
            'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False, 'filters': ['request_id']},
            'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False, 'filters': ['request_id']},
            'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': False, 'filters': ['request_id']},
        },
    }
else:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'loggers': {
            'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
            'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
            'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        },
    }

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
