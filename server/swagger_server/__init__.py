import connexion
import datetime

from swagger_server import encoder

from comanage_api import ComanageApi

from fss_utils.jwt_validate import ValidateCode, JWTValidator

from swagger_server.database import metadata
from swagger_server.database import DISABLE_DATABASE, engine
from swagger_server.database.load_data import load_people_data, load_version_data

from .config import config_from_file, config_from_env

from .database import __VERSION__, log

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
# COmanage ORG
CO_NAME = app_params.get("co_name")
# SSH Key Authenticator ID
CO_SSH_AUTHENTICATOR_ID = app_params.get("co_ssh_authenticator_id")

co_api = ComanageApi(
    co_api_url=CO_REGISTRY_URL,
    co_api_user=COAPI_USER,
    co_api_pass=COAPI_KEY,
    co_api_org_id=COID,
    co_api_org_name=CO_NAME,
    co_ssh_key_authenticator_id=CO_SSH_AUTHENTICATOR_ID
)

# get SSH key parameters
SSH_KEY_ALGORITHM = "rsa"  # can use 'rsa', 'dsa' or 'ecdsa'
SSH_KEY_STORAGE = "local"  # can be 'local' or 'comanage'
SSH_BASTION_KEY_VALIDITY_DAYS = 2
SSH_GARBAGE_COLLECT_AFTER_DAYS = 10
SSH_KEY_SECRET = "secret"
if app_params.get('key_algorithm', None) is not None:
    SSH_KEY_ALGORITHM = app_params.get('key_algorithm')
if app_params.get('key_storage', None) is not None:
    SSH_KEY_STORAGE = app_params.get('key_storage')
if app_params.get('key_validity', None) is not None:
    SSH_BASTION_KEY_VALIDITY_DAYS = app_params.get('key_validity')
if app_params.get('key_garbage_collect', None) is not None:
    SSH_GARBAGE_COLLECT_AFTER_DAYS = app_params.get('key_garbage_collect')
if app_params.get('key_secret', None) is not None:
    SSH_KEY_SECRET = app_params.get('key_secret')

# for testing e.g. comanage code we don't need the database running
if not DISABLE_DATABASE:
    if USER_DB_DROP:
        log.info("Dropping all database tables")
        metadata.drop_all(engine)
    # create tables (should be idempotent)
    log.info("Creating database tables")
    metadata.create_all(engine)

    # load version data
    log.info("Loading version table")
    load_version_data()

# Load user data
log.info(f"Loading {LOAD_USER_DATA} user data")
load_people_data(LOAD_USER_DATA)

# Flask initialization for uwsgi (so it can find swagger_server:app)
app = connexion.App(__name__, specification_dir='./swagger/')
app.app.json_encoder = encoder.JSONEncoder
app.add_api('swagger.yaml', arguments={'title': 'FABRIC User Information Service'}, pythonic_params=True)
