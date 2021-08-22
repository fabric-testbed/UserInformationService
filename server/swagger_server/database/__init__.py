#!/usr/bin/env python3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from ..config import config_from_file, config_from_env

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

DISABLE_DATABASE = False
if db_params.get('disable_database', None) == 'true':
    DISABLE_DATABASE = True

# even if database is disabled its harmless and then imports everywhere are not affected
print(f"Creating POSTGRES ENGINE with parameters {db_params}")
POSTGRES_ENGINE = 'postgres://' + db_params['user'] + ':' + db_params['password'] \
                  + '@' + db_params['host'] + ':' + db_params['port'] \
                  + '/' + db_params['db']

engine = create_engine(POSTGRES_ENGINE)
Session = sessionmaker(bind=engine)
Base = declarative_base()
metadata = Base.metadata

TIMEZONE = 'America/New_York'
