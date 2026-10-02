"""
Configuración de PoliDrive (proyecto Django "driveclone").

Todo lo que cambia entre tu computadora y el servidor (EC2 / RDS / S3) se
lee del archivo .env  ->  ver .env.example
"""

from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# SEGURIDAD
# ------------------------------------------------------------------
SECRET_KEY = config('SECRET_KEY', default='clave-insegura-solo-para-desarrollo-CAMBIAR')
DEBUG = config('DEBUG', default=True, cast=bool)
# En producción: dominio / IP pública de la EC2, ej. ALLOWED_HOSTS=3.90.10.20,midominio.com
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())
# Solo si sirven por HTTPS con dominio, ej. CSRF_TRUSTED_ORIGINS=https://midominio.com
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# ------------------------------------------------------------------
# APPS
# ------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'files',
]

# Usuario propio: tabla "usuarios", login con correo.
AUTH_USER_MODEL = 'files.Usuario'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'driveclone.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'files.context_processors.storage_ctx',
            ],
        },
    },
]

WSGI_APPLICATION = 'driveclone.wsgi.application'

# ------------------------------------------------------------------
# CONTRASEÑAS: hash BCrypt (con PBKDF2 como respaldo para leer hashes viejos)
# ------------------------------------------------------------------
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------------------------------------------------------
# BASE DE DATOS
#   - Sin variables DB_*  -> SQLite local (para desarrollar sin instalar nada).
#   - Con variables DB_*  -> MySQL en Amazon RDS (producción).
#
#   DB_ENGINE=django.db.backends.mysql
#   DB_NAME=polidrive
#   DB_USER=admin
#   DB_PASSWORD=<contraseña de RDS>
#   DB_HOST=<endpoint de RDS>.rds.amazonaws.com
#   DB_PORT=3306
# ------------------------------------------------------------------
DB_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': config('DB_NAME', default=str(BASE_DIR / 'db.sqlite3')),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}
if DB_ENGINE.endswith('mysql'):
    DATABASES['default']['OPTIONS'] = {'charset': 'utf8mb4'}

# ------------------------------------------------------------------
# ALMACENAMIENTO DE ARCHIVOS
#   - Sin AWS_STORAGE_BUCKET_NAME -> disco local (carpeta media/), para desarrollo.
#   - Con AWS_STORAGE_BUCKET_NAME -> Amazon S3.
#
# En la EC2 NO se ponen llaves de acceso: se usa el IAM Role de la instancia
# y boto3 obtiene las credenciales solo. (AWS_ACCESS_KEY_ID/SECRET son
# opcionales, solo por si quieres probar S3 desde tu PC.)
# El bucket debe ser PRIVADO: Django valida permisos y entrega el archivo.
# ------------------------------------------------------------------
AWS_BUCKET = config('AWS_STORAGE_BUCKET_NAME', default='')

if AWS_BUCKET:
    AWS_STORAGE_BUCKET_NAME = AWS_BUCKET
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    _aws_key = config('AWS_ACCESS_KEY_ID', default='')
    if _aws_key:
        AWS_ACCESS_KEY_ID = _aws_key
        AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    _default_storage = {'BACKEND': 'storages.backends.s3.S3Storage'}
else:
    _default_storage = {'BACKEND': 'django.core.files.storage.FileSystemStorage'}

STORAGES = {
    'default': _default_storage,
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

# Solo se usa cuando NO hay S3 (desarrollo local).
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ------------------------------------------------------------------
# INTERNACIONALIZACIÓN / ESTÁTICOS
# ------------------------------------------------------------------
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Matamoros'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dash'
LOGOUT_REDIRECT_URL = 'login'
