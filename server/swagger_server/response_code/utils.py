#!/usr/bin/env python3
from swagger_server.database import Session
import psycopg2
import uuid
import json

from swagger_server.models.people_long import PeopleLong
from swagger_server import log


def dict_from_query(query=None):
    session = Session()
    a = None
    try:
        resultproxy = session.execute(query)
        d, a = {}, []
        for rowproxy in resultproxy:
            # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
            for column, value in rowproxy.items():
                # build up the dictionary
                d = {**d, **{column: value}}
            a.append(d)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if session is not None:
            session.close()

    return a


def run_sql_commands(commands):
    session = Session()
    try:
        if isinstance(commands, tuple):
            for command in commands:
                session.execute(command)
        else:
            session.execute(commands)
        session.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if session is not None:
            session.close()


def validate_uuid_by_oidc_claim(uuid):
    """
    Extract OIDC claim sub from header identity token and match against UUID. Return True
    if match, False othewise.
    If no entry exists, create one and return True.
    :param uuid: uuid to match against
    """
    return True


def validate_oidc_claim(oidc_claim_sub):
    """
    Extract OIDC claim sub from header identity token and compare against parameter. Return
    True if match, False otherwise.
    :param oidc_claim_sub: oidc claim sub
    """
    return True


def create_new_person():
    """
    Extract info from identity token and create (enter in db) an entry for this person,
    including a new UUID.
    :return ps: a PeopleLong entry for the new user
    """
    pl = PeopleLong()
    pl.uuid = uuid.uuid4()
    log.info(f"Creating a new person with UUID {uuid}")
    return pl


def dict_from_json_handle_none(j):
    """
    Convert json into object (dict). If none, return empty dict
    """
    if j is None:
        return dict()
    return json.loads(j)
