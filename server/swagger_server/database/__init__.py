#!/usr/bin/env python3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import config_from_file, config_from_env

# Setup database engine
PREFIX = "POSTGRES"

params = config_from_env(PREFIX)

POSTGRES_ENGINE = 'postgres://' + params['user'] + ':' + params['password'] \
                  + '@' + params['host'] + ':' + params['port'] \
                  + '/' + params['db']

engine = create_engine(POSTGRES_ENGINE)
Session = sessionmaker(bind=engine)

TIMEZONE = 'America/New_York'
