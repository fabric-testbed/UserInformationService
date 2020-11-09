import connexion
import os
import logging
from swagger_server import encoder

from swagger_server.database.models import metadata
from swagger_server.database import engine
from swagger_server.database.load_mock_data import load_people_data, load_version_data

from .config import config_from_file

log = logging.getLogger("User Information Service")

# create tables (should be idempotent)
log.info("Creating tables")
metadata.create_all(engine)

# load version data
log.info("Loading version table")
load_version_data()

# load data if mock
MOCK_SERVICE = False
if os.getenv('UISERVICE_MOCK') == 'true':
    log.info("Loading mock people")
    load_people_data()
    MOCK_SERVICE = True

# Flask initialization for uwsgi (so it can find swagger_server:app)
app = connexion.App(__name__, specification_dir='./swagger/')
app.app.json_encoder = encoder.JSONEncoder
app.add_api('swagger.yaml', arguments={'title': 'FABRIC User Information Service'}, pythonic_params=True)

# Setup COmanage LDAP connection
#CONFIG_FILE = 'swagger_server/ini/pr_comanage.ini'
#CONFIG_SECTION = 'ldap'

#LDAP_PARAMS = config(filename=CONFIG_FILE, section=CONFIG_SECTION)