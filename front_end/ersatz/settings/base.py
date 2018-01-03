# Django settings for ersatz project.
from unipath import Path
from subprocess import check_output
from kombu import Queue

DEBUG = False

ADMINS = (('Lucy', 'lucy@ersatzlabs.com'), ('Dave', 'dave@ersatzlabs.com'))

DEFAULT_FROM_EMAIL = 'Ersatz Team<no-reply@ersatzlabs.com>'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = '587'
EMAIL_HOST_USER = 'davebs'
EMAIL_HOST_PASSWORD = '7sixhorseSheep3?'
ALLOWED_HOSTS = ('api.ersatz1.com', 'api.ersatzlabs.com', '54.187.68.192')
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'ersatz',                      # Or path to database file if using sqlite3.
        'USER': 'ersatz',                      # Not used with sqlite3.
        'PASSWORD': 'ija9fj432ertuerthjfsa',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Dawson'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

PROJECT_DIR = Path(__file__).ancestor(3)
# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = PROJECT_DIR.child('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = PROJECT_DIR.child('static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7gzn11qzf2q!e6cup9r31ydyu75it2!9qxmkf@hixg53d^ml%g'


REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 1
REDIS_PASSWORD = 'FwXCALqGyUyIZ382KKv7KneFmJgis7SALyR3xGG7AZvUMdHT58FLZ3z2RH9JvnXprx3NIVwHesszq9U7CFkCZWuC6pES1HqbE4mS'

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '%s:%s:%s' % (REDIS_HOST, REDIS_PORT, REDIS_DB),
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
            'PASSWORD': REDIS_PASSWORD
        }
    }
}
# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'api.middleware.LoggingMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'ersatz.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'ersatz.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'web',
    'api',
    'job',
    'django.contrib.admin',
    'gunicorn',
    'south',
    'django_extensions',
    'compressor',
    'payments',
    'help',
    'data_management',
    'core',
    'rest_framework',
    'rest_framework_swagger',
    'corsheaders',
    # Uncomment the next line to enable the admin:
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOG_FILE = PROJECT_DIR.child('log', 'server.log')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'exclude_not_allowed_host': {
            '()': 'core.utils.ExcludeNotAllowedHost'
        },
        'require_test_run_false': {
            '()': 'core.utils.RequireTestRunFalse'
        },
    },
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'logfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILE,
            'maxBytes': 5000000,
            'backupCount': 5,
            'formatter': 'standard',
            'filters': ['require_test_run_false']
        },
        'console':{
            'level':'INFO',
            'class':'logging.StreamHandler',
            'formatter': 'standard'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false', 'exclude_not_allowed_host'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers':['console'],
            'propagate': True,
            'level':'WARN',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        #'pika.channel': {
            #'handlers': ['console'],
            #'level': 'DEBUG',
        #},
        #'pika.connection': {
            #'handlers': ['console'],
            #'level': 'DEBUG',
        #},
        'api.request': {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': False
        },
        'api': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        'job': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

INTERCOM_API_SECRET = 'bUMxZ3gh_TAwDFYD-FTfAt2PhYOWZl7jZA9QQxOs'
INVITE_KEYS = ('ab748jdcu8492813', 'ersatzbeta')
AWS_ACCESS_KEY = 'AKIAJ2Z5C7C2QXRNFX5Q'
AWS_SECRET_KEY = '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'
S3_BUCKET = 'ersatz1test'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGIN_URL = '/'
AUTH_USER_MODEL = 'web.ApiUser'
MAX_UPLOAD_SIZE = 1004857600 # 1000Mb

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "ersatz"
BROKER_PASSWORD = "ija9fj432ertuerthjfsa"
BROKER_VHOST = "ersatz"
QUEUE_EXCHANGE = "ersatz"

WORKER_KEY = "uZ3uxJ6eaRxjTyX7uU1"
# billing, money in cents
MIN_USD_RATIO = 41 # cent
BULK_DISCOUNT = ((20000, 10), (50000, 20), (100000, 30)) # cents, discount %
SIGNUP_MINUTES = 180 # gift for new user

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
    'web.context_processors.version',
    'web.context_processors.socketurl',
)

DMWORKER_VERSION = 3
DMWORKER_CELERY_CONFIG = {
    'BROKER_URL': 'amqp://ersatz:ija9fj432ertuerthjfsa@localhost:5672/dmworker',
    'CELERY_RESULT_BACKEND': 'amqp',
    'CELERY_TASK_SERIALIZER': 'json',
    'CELERY_RESULT_SERIALIZER': 'json',
    'CELERY_TIMEZONE': 'America/Dawson',
    'CELERY_ENABLE_UTC': True,
    'CELERY_DEFAULT_QUEUE': 'default',
    'CELERY_QUEUES': (
        Queue('default',    routing_key='task.#'),
        Queue('parser', routing_key='parse.#'),
    ),
    'CELERY_DEFAULT_EXCHANGE': 'tasks',
    'CELERY_DEFAULT_EXCHANGE_TYPE': 'topic',
    'CELERY_DEFAULT_ROUTING_KEY': 'task.default',
    'CELERY_ROUTES': {
            'dmworker.tasks.parse': {
                'queue': 'parser',
                'routing_key': 'parse.datafile',
            },
    }
}
DATASET_VERSION = 2

WS_SERVER_URL = '/sockjs'
WS_SECRET_KEY = 'iqfESjlXHbcnTp7ZTym5n3Wc1AHfLs7fob834bH5vQ83nwsFPqdGC7ZhmxGr'
WS_SALT = 'vMJBIfZ785RtNtw'
WS_PORT = 8887

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend', ),
}

SWAGGER_SETTINGS = {
    "exclude_namespaces": [], # List URL namespaces to ignore
    "api_version": '0.1',  # Specify your API's version
    "api_path": "/",  # Specify the path to your API not a root level
    "enabled_methods": [  # Specify which methods to enable in Swagger UI
        'get',
        'post',
        'put',
        'patch',
        'delete'
    ],
    "is_authenticated": True,  # Set to True to enforce user authentication,
    "is_superuser": True,  # Set to True to enforce admin only access
}

try:
    VERSION = check_output(['git', 'log', '--pretty=format:%ad-%h', '--date=short', '-1'])
except:
    VERSION = '000'

DATA_FILE_EXT = (
    '.ts', '.ts.gz', '.ts.bz', '.ts.bz2',
    '.csv', '.csv.gz', '.csv.bz', '.csv.bz2',
    '.tar.gz', '.tar.bz', '.tar.bz2', '.zip'
)

DATA_FILE_PLAIN_EXT = ('.ts', '.csv')

CORS_ORIGIN_ALLOW_ALL = True

PRODUCTION = False

SOCKET_URL = 'localhost:4000'
