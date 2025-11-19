from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables del .env
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# Dominio público en Railway (si está definido como variable de entorno)
RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")

# Si Railway expone la variable, la usamos; si no, ponemos el dominio a mano
CSRF_TRUSTED_ORIGINS = []

if RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_DOMAIN}")
else:
    # Ajusta este dominio si tu URL es distinta
    CSRF_TRUSTED_ORIGINS.append("https://pepsico-ot-production.up.railway.app")

# Para producción con DEBUG=False, es buena idea permitir también el host de Railway
if RAILWAY_DOMAIN and RAILWAY_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Apps del proyecto
    "taller",
    "ot.apps.OtConfig",
    "reportes",
    "widget_tweaks",
    "core.apps.CoreConfig",
    "inventario.apps.InventarioConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.CurrentUserMiddleware",
    "config.middlewares.NoCacheMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # carpeta global de templates
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.notif_count",
                'core.context_processors.unread_notifications',

            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ==========
# Base de Datos (SQLite en dev por simplicidad)
# ==========
db_engine = os.getenv("DB_ENGINE", "sqlite")
if db_engine == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ==========
# Passwords / i18n
# ==========
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"  # o "es"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# ==========
# Static & Media
# ==========
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]  # para archivos estáticos locales (opcional)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==========
# Mensajes y Auth
# ==========
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Seguridad mínima (endurecer en prod)
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

# === Subidas de archivos ===
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))  # 10 MB por defecto
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

LOGIN_REDIRECT_URL = "/"    # A dónde se redirige al iniciar sesión
LOGOUT_REDIRECT_URL = "/login/"  # A dónde se redirige al cerrar sesión
LOGIN_URL = "/login/"        # Página de inicio de sesión predeterminada

# 15 minutos de inactividad
SESSION_COOKIE_AGE = 15 * 60      # 900 segundos
SESSION_SAVE_EVERY_REQUEST = True