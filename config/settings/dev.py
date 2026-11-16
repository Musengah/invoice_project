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
