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
from typing import Tuple, Any, List

import psycopg2
import uuid
import json
import re
import jwt
import datetime
import requests
from requests.auth import HTTPBasicAuth

from fss_utils.jwt_manager import ValidateCode
from swagger_server.models import Preferences, PeopleShort
from swagger_server.models.people_long import PeopleLong
from swagger_server.database import Session
from swagger_server.database.models import FabricPerson, InsertOutcome, insert_unique_person
from swagger_server import SKIP_CILOGON_VALIDATION, COAPI_KEY, COAPI_USER, COID, \
    CO_REGISTRY_URL, CO_ACTIVE_USERS_COU, log
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


def any_authenticated_user(headers) -> bool:
    """
    Validate that user is authenticated, i.e. a valid token is present in
    the header.
    :param headers: request headers
    """
    if SKIP_CILOGON_VALIDATION:
        log.info("Skipping authentication check")
        return True
    else:
        log.info("Validating that user is authenticated")

    id_token = headers.get(ID_TOKEN_NAME)
    if id_token is None:
        log.warn("Authentication token not present in header")
        return False

    # validate the token
    if jwt_validator is not None:
        log.info("Validating CI Logon token")
        code, e = jwt_validator.validate_jwt(token=id_token)
        if code is not ValidateCode.VALID:
            log.error(f"Unable to validate provided token: {code}/{e}")
            return False
    else:
        log.warning("JWT Token validator not initialized, skipping validation")
        return False
    return True


def validate_uuid_by_oidc_claim(headers, puuid) -> bool:
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
        code, e = jwt_validator.validate_jwt(token=id_token)
        if code is not ValidateCode.VALID:
            log.error(f"Unable to validate provided token: {code}/{e}")
            return False
    else:
        log.warning("JWT Token validator not initialized, skipping validation")

    decoded = jwt.decode(id_token, verify=False)
    oidc_claim_sub = decoded.get(SUB_CLAIM, None)

    if oidc_claim_sub is None:
        log.error('"sub" claim not present in the decoded token')
        return False

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


def validate_oidc_claim(headers, oidc_claim_sub) -> bool:
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
        code, e = jwt_validator.validate_jwt(token=id_token)
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
    decoded = None
    if jwt_validator is not None:
        log.info("Validating CI Logon token")
        code, decoded = jwt_validator.validate_jwt(token=id_token)
        if code is not ValidateCode.VALID:
            log.error(f"Unable to validate provided token: {code}/{decoded}")
            return None
    else:
        log.warning("JWT Token validator not initialized, skipping validation")
        decoded = jwt.decode(id_token, verify=False)

    header_sub = decoded.get(SUB_CLAIM, None)

    log.info(f"Extracted sub from token: {header_sub}")
    return header_sub


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


def comanage_list_people_matches(given: str = None, family: str = None, email: str = None) -> Tuple[int, List]:
    """
    Try to get a brief list of people matching one or more of these fields.
    Returns a tuple of status code and a list of matching CoPeople entries (if any)
    """
    params = {'coid': str(COID)}
    if given is not None:
        params['given'] = given
    if family is not None:
        params['family'] = family
    if email is not None:
        params['mail'] = email
    # don't allow to ask stupid questions
    if len(params.keys()) == 1:
        return 500, []
    try:
        response = requests.get(url=CO_REGISTRY_URL + 'co_people.json',
                                params=params,
                                auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
    except requests.exceptions.RequestException as e:
        log.debug(f"COmanage request exception {e} encountered in co_people.json, "
                  f"returning status 500")
        return 500, []

    if response.status_code == 204:
        # we got nothing back
        return 200, []
    if response.status_code != 200:
        return response.status_code, []
    response_obj = response.json()
    return response.status_code, response_obj['CoPeople']


def comanage_check_person_couid(person_id, couid) -> Tuple[int, bool]:
    """
    Check if a given person is a member of couid. Return tuple of API status code
    and True or False. Strings or integers accepted as parameters
    """
    assert person_id is not None
    assert couid is not None
    params = {'coid': str(COID), 'copersonid': str(person_id)}
    try:
        response = requests.get(url=CO_REGISTRY_URL + 'co_person_roles.json',
                                params=params, auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
    except requests.exceptions.RequestException as e:
        log.debug(f"COmanage request exception {e} encountered in co_person_roles.json, "
                  f"returning status 500")
        return 500, False
    if response.status_code == 204:
        # we got nothing back, just say so
        return 200, False
    if response.status_code != 200:
        return response.status_code, False
    response_obj = response.json()
    if response_obj.get('CoPersonRoles', None) is None:
        log.debug(f"COmanage request returned no personal roles in co_person_roles.json")
        return 500, False
    for role in response_obj['CoPersonRoles']:
        if role.get('CouId', None) is not None and role['CouId'] == str(couid):
            return response.status_code, True
    return response.status_code, False


def comanage_check_active_person(person) -> Tuple[int, bool or None, str or None]:
    """
    Try to figure out person's co_person_id from different attributes.
    Returns COmanage status code, a boolean for whether person is active
    and string id to store back in the database for next time.
    """
    # if person_id is present, skip the line
    if person.co_person_id is not None:
        log.debug(f'Checking person {person.oidc_claim_sub} active status by co_person_id '
                  f'with person id {person.co_person_id} against active COU {CO_ACTIVE_USERS_COU}')
        code, active_flag = comanage_check_person_couid(person.co_person_id, CO_ACTIVE_USERS_COU)

        # if everything OK and user active, return immediately, otherwise
        # fall through and try to find the person and update their co_person_id (may happen
        # if they were purged from comanage)
        if code == 200 and active_flag:
            return code, active_flag, None

    # if email is present, try that first
    people_list = []
    person_id = None
    email = person.email if person.email is not None else person.eppn
    if email is not None:
        log.debug(f'Checking person {person.oidc_claim_sub} active status by searching via email {email}')
        # easiest if there is email
        code, people_list = comanage_list_people_matches(email=email)
        if code == 204:
            # nothing found
            return 200, False, None
        if code != 200:
            return code, False, None
    else:
        if person.name is not None:
            name_split = person.name.split(' ')
            fname = name_split[0]
            if len(name_split) == 2:
                lname = name_split[1]
            else:
                lname = name_split[2]
            # try to find by fname, lname
            log.debug(f'Checking person {person.oidc_claim_sub} active status '
                      f'by searching fname, lname {fname} {lname}')
            code, people_list = comanage_list_people_matches(given=fname, family=lname)
            if code == 204:
                # nothing found
                return 200, False, None
            if code != 200:
                return code, False, None
    person_id = None
    oidcsub_found = False
    for people in people_list:
        # find a match for person.oidc_claim_sub
        person_id = people.get('Id', None)
        if person_id is None:
            continue
        oidcsub = comanage_get_person_identifier(person_id, 'oidcsub')
        if oidcsub is not None:
            oidcsub_found = True
        if oidcsub == person.oidc_claim_sub:
            break
        person_id = None
    if person_id is None:
        log.debug(f'Unable to identify a person {person.oidc_claim_sub} from the list (of length {len(people_list)}) '
                  f'of COmanage matches. OIDC sub found flag is {oidcsub_found}.')
        # person id not available
        return 200, False, None
    code, active_flag = comanage_check_person_couid(person_id, CO_ACTIVE_USERS_COU)
    return code, active_flag, person_id


def comanage_get_person_name(co_person_id) -> Tuple[int, str or None]:
    """
    Sometimes CILogon doesn't give us a person name initially, but
    it should be there after enrollment in COmanage.
    We provide co_person_id externally as it may or may not
    be already stored on the person.
    :return: tuple of comanage return code and name if any
    """
    assert co_person_id is not None
    params = {'copersonid': co_person_id}
    response = requests.get(url=CO_REGISTRY_URL + 'names.json',
                            params=params,
                            auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
    if response.status_code == 204:
        # we got nothing back, just say so
        return 200, None
    if response.status_code != 200:
        return response.status_code, None
    response_obj = response.json()
    names_list = response_obj.get('Names', None)
    if names_list is None or len(names_list) == 0:
        return 200, None
    # use the first name entry
    names = names_list[0]
    name = "".join([names['Given'], ' ', names['Middle'], ' ',
                    names['Family'], ' ', names['Suffix']])
    # strip extra spaces
    name = re.sub(' +', ' ', name)
    return 200, name[:-1]


def check_user_active(session, headers) -> Tuple[int, bool]:
    """
    Check the user with this oidc_claim sub is active. DB Session
    is passed in externally. No commits required - doesn't change db.
    """
    oidc_claim_sub = extract_oidc_claim(headers)
    query = session.query(FabricPerson).filter(FabricPerson.oidc_claim_sub == oidc_claim_sub)
    query_result = query.all()

    person = query_result[0]
    # check with COmanage they are an active user
    status, active_flag, _ = comanage_check_active_person(person)
    return status, active_flag


def comanage_get_person_identifier(co_person_id, identifier_type) -> str or None:
    """
    Get a specific type of identifier about this co_person_id:
    identifer can be for example 'eppn', 'eptid', 'oidcsub', 'sorid',
    'fabricalphaid'
    """
    assert co_person_id is not None
    assert identifier_type is not None

    params = {'copersonid': co_person_id}
    response = requests.get(url=CO_REGISTRY_URL + 'identifiers.json',
                            params=params,
                            auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
    person_id = None
    if response.status_code == requests.codes.ok:
        data = response.json()
        for identifier in data['Identifiers']:
            if identifier['Type'] == identifier_type:
                person_id = identifier['Identifier']
                break
    else:
        log.debug(f'Received code {response.status_code} when calling COmanage identifiers.json')
    return person_id
