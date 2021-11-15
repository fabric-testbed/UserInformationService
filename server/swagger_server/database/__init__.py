#!/usr/bin/env python3
__VERSION__ = "1.0.1"

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from comanage_api import ComanageApi

from ..config import config_from_file, config_from_env

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("User Information Service")

# Setup database engine
DB_PARAM_PREFIX = "POSTGRES"
LDAP_PARAM_PREFIX = "LDAP"
APP_PREFIX = "UIS"

db_params = config_from_env(DB_PARAM_PREFIX)
ldap_params = config_from_env(LDAP_PARAM_PREFIX)
comanage_params = config_from_env(APP_PREFIX)

# this is a replica of top-level init code, here to avoid circular dependencies
# setup to query COmanage APIs
COAPI_USER = comanage_params.get("coapi_user")
COAPI_KEY = comanage_params.get("coapi_key")
COID = comanage_params.get("coid")
CO_ACTIVE_USERS_COU = comanage_params.get("co_active_users_cou")
CO_REGISTRY_URL = comanage_params.get("co_registry_url")
CO_NAME = comanage_params.get("co_name")
CO_SSH_AUTHENTICATOR_ID = comanage_params.get("co_ssh_authenticator_id")

co_api = ComanageApi(
    co_api_url=CO_REGISTRY_URL,
    co_api_user=COAPI_USER,
    co_api_pass=COAPI_KEY,
    co_api_org_id=COID,
    co_api_org_name=CO_NAME,
    co_ssh_key_authenticator_id=CO_SSH_AUTHENTICATOR_ID
)

DISABLE_DATABASE = False
if db_params.get('disable_database', None) == 'true':
    DISABLE_DATABASE = True

# even if database is disabled its harmless and then imports everywhere are not affected
print(f"Creating POSTGRES ENGINE with parameters {db_params}")
POSTGRES_ENGINE = 'postgres://' + db_params['user'] + ':' + db_params['password'] \
                  + '@' + db_params['host'] + ':' + db_params['port'] \
                  + '/' + db_params['db']

DB_POOL_SIZE = int(db_params("pool_size"))
# set overflow 10% of pool size
DB_OVERFLOW = int(DB_POOL_SIZE * 0.1)
if DB_OVERFLOW == 0:
    DB_OVERFLOW = 10

engine = create_engine(POSTGRES_ENGINE, pool_size=DB_POOL_SIZE, max_overflow=DB_OVERFLOW)
Session = sessionmaker(bind=engine)
Base = declarative_base()
metadata = Base.metadata

TIMEZONE = 'America/New_York'
