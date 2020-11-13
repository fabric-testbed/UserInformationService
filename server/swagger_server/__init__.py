import connexion
import os
import logging
from swagger_server import encoder

from swagger_server.database.models import metadata
from swagger_server.database import engine
from swagger_server.database.load_data import load_people_data, load_version_data

from .config import config_from_file

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("User Information Service")

# create tables (should be idempotent)
log.info("Creating tables")
metadata.create_all(engine)

# load version data
log.info("Loading version table")
load_version_data()

SKIP_CILOGON_VALIDATION = True
if os.getenv('SKIP_CILOGON_VALIDATION') == 'false':
    SKIP_CILOGON_VALIDATION = False

LOAD_USER_DATA = 'none'
if os.getenv('USER_DATA') == 'mock':
    LOAD_USER_DATA = 'mock'
elif os.getenv('USER_DATA') == 'ldap':
    LOAD_USER_DATA = 'ldap'

log.info(f"Loading {LOAD_USER_DATA} user data")
load_people_data(LOAD_USER_DATA)

# Flask initialization for uwsgi (so it can find swagger_server:app)
app = connexion.App(__name__, specification_dir='./swagger/')
app.app.json_encoder = encoder.JSONEncoder
app.add_api('swagger.yaml', arguments={'title': 'FABRIC User Information Service'}, pythonic_params=True)
