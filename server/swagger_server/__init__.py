__VERSION__ = "1.0"

import connexion
import logging
import datetime

from swagger_server import encoder

from fss_utils.jwt_validate import ValidateCode, JWTValidator

from swagger_server.database.models import metadata
from swagger_server.database import DISABLE_DATABASE, engine
from swagger_server.database.load_data import load_people_data, load_version_data

from .config import config_from_file, config_from_env

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("User Information Service")

# for testing e.g. comanage code we don't need the database running
if not DISABLE_DATABASE:
    # create tables (should be idempotent)
    log.info("Creating database tables")
    metadata.create_all(engine)

    # load version data
    log.info("Loading version table")
    load_version_data()

# load app configuration parameters
APP_PARAM_PREFIX = "UIS"
app_params = config_from_env(APP_PARAM_PREFIX)

# query limit
QUERY_LIMIT = 20
if app_params.get('query_limit', None) is not None:
    QUERY_LIMIT = int(app_params.get('query_limit'))
log.info(f'Using a search limit of {QUERY_LIMIT} entries for /people queries')

SKIP_CILOGON_VALIDATION = True
if app_params.get('skip_cilogon_validation', None) == 'false':
    SKIP_CILOGON_VALIDATION = False

LOAD_USER_DATA = 'none'
if app_params.get('user_data', None) == 'mock':
    LOAD_USER_DATA = 'mock'
elif app_params.get('user_data', None) == 'ldap':
    LOAD_USER_DATA = 'ldap'
elif app_params.get('user_data', None) == 'rest':
    LOAD_USER_DATA = 'rest'

USER_DB_DROP = False
if app_params.get('user_db_drop', None) == 'true' or \
        app_params.get('user_db_drop', None) == 'yes':
    USER_DB_DROP = True

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
    jwt_validator = JWTValidator(url=CILOGON_CERTS,
                                 refresh_period=datetime.timedelta(hours=t.hour,
                                                                   minutes=t.minute,
                                                                   seconds=t.second))
else:
    jwt_validator = None

# setup to query COmanage APIs
# key and user for accessing API
COAPI_USER = app_params.get("coapi_user")
COAPI_KEY = app_params.get("coapi_key")
# id of the CO we are working with
COID = app_params.get("coid")
# id of the group representing FABRIC active users in COmanage
CO_ACTIVE_USERS_COU = app_params.get("co_active_users_cou")
# registry URL
CO_REGISTRY_URL = app_params.get("co_registry_url")

# Load user data
log.info(f"Loading {LOAD_USER_DATA} user data")
load_people_data(LOAD_USER_DATA, USER_DB_DROP)

# Flask initialization for uwsgi (so it can find swagger_server:app)
app = connexion.App(__name__, specification_dir='./swagger/')
app.app.json_encoder = encoder.JSONEncoder
app.add_api('swagger.yaml', arguments={'title': 'FABRIC User Information Service'}, pythonic_params=True)
