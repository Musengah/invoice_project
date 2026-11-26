import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Local development defaults to SQLite. Set DATABASE_URL (for example to a
# Neon connection string) to develop against a real PostgreSQL database.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ======================================================================
# FILE: config/settings/prod.py
# ======================================================================
import os

import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", "sqlite:///db.sqlite3"),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
}

STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 20  # fail fast instead of hanging the gunicorn worker
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# Render's free tier blocks outbound SMTP ports (25, 465, 587), so plain
# SMTP connections hang there. Set BREVO_API_KEY to send email (password
# reset, etc.) over Brevo's HTTPS API instead, which is unaffected.
# DEFAULT_FROM_EMAIL must be a sender email you verified in Brevo.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
if BREVO_API_KEY:
    EMAIL_BACKEND = "invoices.email_backends.BrevoEmailBackend"

# --- Transport and browser security (required behind Render's proxy) ---
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True