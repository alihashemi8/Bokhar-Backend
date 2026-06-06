import os
from datetime import timedelta
from pathlib import Path

from decouple import config

NESHAN_API_KEY = config("NESHAN_API_KEY")
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

BASE_DIR = Path(__file__).resolve().parent.parent

ALLOWED_HOSTS = ['bokhar.online', 'www.bokhar.online', 'backend', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third Party
    "django_extensions",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_results",
    "django_prometheus",
    "drf_spectacular",

    # Local Apps
    "users",
    "products",
    "discounts",
    "order",
    "notifications",
    "report",
<<<<<<< HEAD:bokhar/settings.py
    "wallet"
=======
    #"wallet"
>>>>>>> 5d5e438613b77593787065d13dc4280c68c5002d:backend/bokhar/settings.py
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",

    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    # JWT Cookie -> Authorization Header
    "bokhar.middleware.CookieToHeaderMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",

]

ROOT_URLCONF = "bokhar.urls"
from celery.schedules import crontab


CELERY_BEAT_SCHEDULE = {
    # 'run-nightly-settlements-every-day': {
    #     'task': 'wallet.tasks.run_nightly_settlements',
    #     'schedule': crontab(hour=21, minute=30),
    # },
    'report_daily': {
        'task': 'notifications.tasks_seller.send_sms_to_seller_daily_report',
        'schedule': crontab(hour=7, minute=30),
    },

}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "bokhar.wsgi.application"

#----------------------database----------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": "db",
        "PORT": "5432",
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]

AUTHENTICATION_BACKENDS = [
    "users.authenticate.CustomBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LANGUAGE_CODE = "en-us"

# Changed from UTC -> Tehran
TIME_ZONE = "Asia/Tehran"

USE_I18N = True
USE_TZ = True

#--------------------customer user----------------------

AUTH_USER_MODEL = "users.User"

# ---------------- CORS ----------------

# ---------------- CORS & CSRF ----------------
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "https://bokhar.online",
        "https://www.bokhar.online",
    ]
    CSRF_TRUSTED_ORIGINS = [
        "https://bokhar.online",
        "https://www.bokhar.online",
    ]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

# ---------------- DRF ----------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "users.authenticate.CookieJWTAuthentication",
    ],
    # اگر خواستی همه APIها لاگین اجباری باشن:
    # "DEFAULT_PERMISSION_CLASSES": [
    #     "rest_framework.permissions.IsAuthenticated",
    # ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Online Laundry API",
    "DESCRIPTION": "Professional E-Commerce Backend",
    "VERSION": "1.0.0",
    "SECURITY": [
        {
            "BearerAuth": []
        }
    ],

    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    }
}
# ---------------- JWT ----------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # Added from first config
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,

    "AUTH_COOKIE": "access",
    "AUTH_COOKIE_REFRESH": "refresh",

    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SECURE": False,  # True in production with HTTPS
    "AUTH_COOKIE_SAMESITE": "Lax",

    "ACCESS_TOKEN_LIFETIME_SECONDS": int(
        timedelta(hours=1).total_seconds()
    ),
    "REFRESH_TOKEN_LIFETIME_SECONDS": int(
        timedelta(days=7).total_seconds()
    ),
}


# ---------------- LOGGING ----------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler"
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}

# ---------------- CACHE ----------------

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_CACHE_URL"),
    }
}

# ---------------- CELERY ----------------

CELERY_BROKER_URL = config("CELERY_BROKER_URL")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# ---------------- MEDIA ----------------

# Fixed media url
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

#--------------------static----------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------- SESSION ----------------

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True

# ---------------- CSRF ----------------

CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False

#----------------zarinpal setting ------------
"""ZARINPAL = {
    "MERCHANT_ID": "xxxxxxxx",

    "ACCESS_TOKEN": "xxxxxxxx",

    "REQUEST_URL":
        "https://api.zarinpal.com/pg/v4/payment/request.json",

    "VERIFY_URL":
        "https://api.zarinpal.com/pg/v4/payment/verify.json",

    "PAYMENT_URL":
        "https://www.zarinpal.com/pg/StartPay/",

    "CALLBACK_URL":
        "https://example.com/api/payment/verify/",

    "REFUND_URL":
        "https://api.zarinpal.com/pg/v4/payment/refund.json",
}"""


#-------------------------
from opentelemetry import trace

from opentelemetry.sdk.resources import Resource

from opentelemetry.sdk.trace import (
    TracerProvider
)

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor
)

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter
)

resource = Resource.create(
    {
        "service.name": "payment-api",
        "service.version": "1.0.0",
    }
)

provider = TracerProvider(
    resource=resource
)

processor = BatchSpanProcessor(
    OTLPSpanExporter(
        endpoint="http://otel-collector:4317",
        insecure=True,
    )
)

provider.add_span_processor(
    processor
)

trace.set_tracer_provider(
    provider
)