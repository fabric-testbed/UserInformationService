#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#
# Author: Ilya Baldin (ibaldin@renci.org) Michael Stealey (stealey@renci.org)

import psycopg2
import uuid
import json
import jwt
import datetime

from fss_utils.jwt_validate import ValidateCode
from swagger_server.models import Preferences, PeopleShort
from swagger_server.models.people_long import PeopleLong
from swagger_server.database import Session
from swagger_server.database.models import FabricPerson, InsertOutcome, insert_unique_person
from swagger_server import SKIP_CILOGON_VALIDATION, log
from swagger_server import jwt_validator


"""
Module implementing a variety of utility functions for mapping
database entries onto API returns and assisting in authorization.
"""


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


ID_TOKEN_NAME = 'X-Vouch-Idp-Idtoken'
SUB_CLAIM = 'sub'
NAME_CLAIM = 'name'
EMAIL_CLAIM = 'email'


def validate_uuid_by_oidc_claim(headers, puuid):
    """
    Extract OIDC claim sub from header identity token and match against UUID. Return True
    if match, False otherwise.
    :param headers: request headers
    :param puuid: uuid to match against
    :return bool:
    """
    if SKIP_CILOGON_VALIDATION:
        log.info(f"Skipping uuid {puuid} validation")
        return True
    else:
        log.info(f"Validating OIDC claim UUID {puuid} match")

    id_token = headers.get(ID_TOKEN_NAME)
    if id_token is None:
        log.info("ID token absent")
        return False

    # validate the token
    if jwt_validator is not None:
        log.info("Validating CI Logon token")
        code, e = jwt_validator.validate_jwt(id_token)
        if code is not ValidateCode.VALID:
            log.error(f"Unable to validate provided token: {code}/{e}")
            return False
    else:
        log.warning("JWT Token validator not initialized, skipping validation")

    decoded = jwt.decode(id_token, verify=False)
    oidc_claim_sub = decoded.get(SUB_CLAIM)

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.oidc_claim_sub == oidc_claim_sub)
        query_result = query.all()

        if len(query_result) == 0:
            log.error(f"Unable to find user matching claim sub {oidc_claim_sub}")
            return False

        if len(query_result) > 1:
            log.error(f"Found multiple users matching claim sub {oidc_claim_sub}")
            return False

        person = query_result[0]

        log.info(f"Entry for claim sub vs uuid {puuid} match: {person.uuid == puuid}")
        return person.uuid == puuid
    finally:
        session.close()


def validate_oidc_claim(headers, oidc_claim_sub):
    """
    Extract OIDC claim sub from header identity token and compare against parameter. Return
    True if match, False otherwise. Does not touch database.
    :param headers:
    :param oidc_claim_sub: oidc claim sub
    :return bool:
    """
    if SKIP_CILOGON_VALIDATION:
        log.info(f"Skipping OIDC claim sub {oidc_claim_sub} validation")
        return True
    else:
        log.info(f"Validating OIDC claim sub {oidc_claim_sub} match")

    id_token = headers.get(ID_TOKEN_NAME)
    if id_token is None:
        log.info("ID token absent")
        return False

    # validate the token
    if jwt_validator is not None:
        log.info("Validating CI Logon token")
        code, e = jwt_validator.validate_jwt(id_token)
        if code is not ValidateCode.VALID:
            log.error(f"Unable to validate provided token: {code}/{e}")
            return False
    else:
        log.warning("JWT Token validator not initialized, skipping validation")

    decoded = jwt.decode(id_token, verify=False)
    header_sub = decoded.get(SUB_CLAIM)

    log.info(f"Parameter sub vs claim sub match: {header_sub == oidc_claim_sub}")
    return header_sub == oidc_claim_sub


def extract_oidc_claim(headers):
    """
    Extract OIDC claim sub from header identity token and return it.
    :param headers:
    :return string:
    """

    id_token = headers.get(ID_TOKEN_NAME)
    if id_token is None:
        log.info("ID token absent")
        return None

    # validate the token
    if jwt_validator is not None:
        log.info("Validating CI Logon token")
        code, e = jwt_validator.validate_jwt(id_token)
        if code is not ValidateCode.VALID:
            log.error(f"Unable to validate provided token: {code}/{e}")
            return None
    else:
        log.warning("JWT Token validator not initialized, skipping validation")

    decoded = jwt.decode(id_token, verify=False)
    header_sub = decoded.get(SUB_CLAIM)

    log.info(f"Extracted sub from token: {header_sub}")
    return header_sub


def validate_person(headers):
    """
    Validate that this represents a valid FABRIC person based on header information.
    Cookie or identity token can be used.
    :param headers: request headers
    """
    if SKIP_CILOGON_VALIDATION:
        log.info("Skipping person validation")
        return True
    else:
        log.info("Validating FABRIC person")
        # TODO: need to check they are a valid user, but nothing more
        # TODO: get stuff out of id token and or cookie
    return True


def create_new_fabric_person_from_token(headers, check_unique=False):
    """
    Extract info from identity token and create a FabricPerson entry for this person,
    including a new UUID. Return a PeopleLong based on that info.
    :param headers: request headers with cookie, ID token etc
    :param check_unique: check for uniqueness before insert
    :return ps: a PeopleLong entry for the new user or None on error
    """
    id_token = headers.get(ID_TOKEN_NAME)
    # token should be validated by now
    decoded = jwt.decode(id_token, verify=False)

    session = Session()
    try:
        dbperson = FabricPerson()
        dbperson.uuid = uuid.uuid4()
        log.info(f"Generating new entry for user {decoded.get(SUB_CLAIM)} with UUID {dbperson.uuid}")
        dbperson.registered_on = datetime.datetime.utcnow()
        dbperson.oidc_claim_sub = decoded.get(SUB_CLAIM)
        dbperson.name = decoded.get(NAME_CLAIM)
        dbperson.email = decoded.get(EMAIL_CLAIM)
        if check_unique:
            ret = insert_unique_person(dbperson, session)
            if ret == InsertOutcome.OK:
                session.commit()
            else:
                log.error(f"Unable to insert entry for user {decoded.get(SUB_CLAIM)} "
                          f"with UUID {dbperson.uuid} due to {ret}")
                return None
        else:
            session.add(dbperson)
            session.commit()
        pl = fill_people_long_from_person(dbperson)
        return pl
    finally:
        session.close()


def dict_from_json_handle_none(j):
    """
    Convert json into object (dict). If none, return empty dict
    """
    if j is None:
        return dict()
    return json.loads(j)


def fill_people_long_from_person(person):
    """
    Return a PeopleLong based on FabricPerson
    :param person:
    :return pl: a PeopleLong
    """
    response = PeopleLong()

    # construct response object
    response.uuid = person.uuid
    response.name = person.name
    response.email = person.email
    response.oidc_claim_sub = person.oidc_claim_sub
    if person.eppn != 'None':
        response.eppn = person.eppn
    else:
        response.eppn = ''
    response.prefs = Preferences(settings=dict_from_json_handle_none(person.settings),
                                 permissions=dict_from_json_handle_none(person.permissions),
                                 interests=dict_from_json_handle_none(person.interests))
    return response


def fill_people_short_from_person(person):
    """
    Return a PeopleShort based on FabricPerson
    :param person:
    :return ps: a PeopleShort
    """
    ps = PeopleShort()
    ps.email = person.email
    ps.name = person.name
    ps.uuid = person.uuid
    ps.oidc_claim_sub = person.oidc_claim_sub
    if person.eppn != 'None':
        ps.eppn = person.eppn
    else:
        ps.eppn = ''
    return ps