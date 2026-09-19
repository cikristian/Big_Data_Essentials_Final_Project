import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_project_env() -> None:
    """Load simple KEY=VALUE settings from the project-level .env file."""
    env_path = BASE_DIR.parent / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            os.environ.setdefault(name, value)


load_project_env()

SECRET_KEY = "development-only-replace-before-deployment"
DEBUG = True
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "operations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

WSGI_APPLICATION = "config.wsgi.application"

mysql_configured = any(
    [
        os.getenv("MYSQL_DATABASE"),
        os.getenv("MYSQL_USER"),
        os.getenv("MYSQL_PASSWORD"),
        os.getenv("MYSQL_HOST"),
        os.getenv("MYSQL_PORT"),
    ]
)

DATABASES = {
    "default": {
    "ENGINE": "django.db.backends.mysql",
    "NAME": os.getenv("MYSQL_DATABASE", "Rwanda_Public_Transport"),
    "USER": os.getenv("MYSQL_USER", "root"),
    "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
    "HOST": os.getenv("MYSQL_HOST", "localhost"),
    "PORT": os.getenv("MYSQL_PORT", "3306"),
    "OPTIONS": {"charset": "utf8mb4"},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Etc/GMT+2"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TRIP_TOPIC = os.getenv("KAFKA_TRIP_TOPIC", "kigali-trip-events")
