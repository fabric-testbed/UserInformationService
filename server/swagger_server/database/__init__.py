#!/usr/bin/env python3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import config_from_file, config_from_env

# Setup database engine
DB_PARAM_PREFIX = "POSTGRES"
LDAP_PARAM_PREFIX = "LDAP"

db_params = config_from_env(DB_PARAM_PREFIX)
ldap_params = config_from_env(LDAP_PARAM_PREFIX)

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

TIMEZONE = 'America/New_York'
