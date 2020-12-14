import connexion
import os
import logging
import datetime

from swagger_server import encoder

from fss_utils.jwt_validate import ValidateCode, JWTValidator

from swagger_server.database.models import metadata
from swagger_server.database import engine
from swagger_server.database.load_data import load_people_data, load_version_data

from .config import config_from_file, config_from_env

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("User Information Service")

# create tables (should be idempotent)
log.info("Creating tables")
metadata.create_all(engine)

# load version data
log.info("Loading version table")
load_version_data()

# load app configuration parameters
APP_PARAM_PREFIX = "UIS"
app_params = config_from_env(APP_PARAM_PREFIX)

SKIP_CILOGON_VALIDATION = True
if app_params.get('skip_cilogon_validation', None) == 'false':
    SKIP_CILOGON_VALIDATION = False

LOAD_USER_DATA = 'none'
if app_params.get('user_data', None) == 'mock':
    LOAD_USER_DATA = 'mock'
elif app_params.get('user_data', None) == 'ldap':
    LOAD_USER_DATA = 'ldap'
log.info(f"Loading {LOAD_USER_DATA} user data")
load_people_data(LOAD_USER_DATA)

QUERY_CHARACTER_MIN = 3
if app_params.get('search_min_char_count', None) is not None:
    char_min = int(app_params['search_min_char_count'])
    if char_min > 0:
        QUERY_CHARACTER_MIN = char_min
    else:
        log.warning(f'Search character limit of {char_min} is not valid, using default instead.')
log.info(f'Using a search character limit of {QUERY_CHARACTER_MIN} for /people queries')

# initialize CI Logon Token Validation
if not SKIP_CILOGON_VALIDATION:
    CILOGON_CERTS = app_params.get("cilogon_certs")
    CILOGON_KEY_REFRESH = app_params.get("cilogon_key_refresh")
    log.info(f'Initializing JWT Validator to use {CILOGON_CERTS} endpoint, '
             f'refreshing keys every {CILOGON_KEY_REFRESH} HH:MM:SS')
    t = datetime.datetime.strptime(CILOGON_KEY_REFRESH, "%H:%M:%S")
    jwt_validator = JWTValidator(CILOGON_CERTS,
                                 datetime.timedelta(hours=t.hour,
                                                    minutes=t.minute,
                                                    seconds=t.second))
else:
    jwt_validator = None

# Flask initialization for uwsgi (so it can find swagger_server:app)
app = connexion.App(__name__, specification_dir='./swagger/')
app.app.json_encoder = encoder.JSONEncoder
app.add_api('swagger.yaml', arguments={'title': 'FABRIC User Information Service'}, pythonic_params=True)
