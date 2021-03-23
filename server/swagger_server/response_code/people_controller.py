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

from flask import request
from sqlalchemy import or_, and_

from swagger_server.database import Session
from swagger_server.database.models import FabricPerson
from swagger_server.models.people_long import PeopleLong  # noqa: E501
from swagger_server import QUERY_CHARACTER_MIN, QUERY_LIMIT
import swagger_server.response_code.utils as utils
from swagger_server.response_code.utils import log


def people_get(person_name=None):  # noqa: E501
    """list of people
    List of people # noqa: E501
    :param person_name: Search People by Name (ILIKE) or email (ILIKE)
    :type person_name: str
    :rtype: List[PeopleShort]
    """
    person_name = str(person_name).strip()

    # can't let them query by fewer than 5 characters
    if not person_name or len(person_name) < QUERY_CHARACTER_MIN:
        log.error(f'Bad /people request - insufficient information for search')
        return "Must provide more information", 400, \
               {'X-Error': 'Bad request'}

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            log.error(f'Problem {status} contacting COmanage for active user check in /people')
            return f'Error {status} contacting COmanage', 500, \
                   {'X-Error': 'COmanage problem'}
        if not active_flag:
            log.warn(f'User is not an active user in /people')
            return 'User not an active user', 401, \
                   {'X-Error': 'Unauthorized'}

        # query by name and email
        query = session.query(FabricPerson).\
            filter(or_(FabricPerson.name.ilike("%{}%".format(str(person_name))),
            FabricPerson.email.ilike("%{}%".format(str(person_name))))).limit(QUERY_LIMIT)

        query_result = query.all()

        if len(query_result) == 0:
            log.warn(f'No matching users found for {person_name} in /people')
            return 'No matches for people found.', 404, {'X-Error': 'People Not Found'}

        response = []
        for person in query_result:
            ps = utils.fill_people_short_from_person(person)
            response.append(ps)

        return response
    finally:
        session.close()


def people_whoami_get():  # noqa: E501
    """
    Self details by OIDC Claim sub contained in token# noqa: E501
    If a person doesn't exist, it gets created.
    :rtype: PeopleLong
    """
    # trust the token, get claim sub from it
    oidc_claim_sub = utils.extract_oidc_claim(request.headers)
    if oidc_claim_sub is None:
        log.error(f'No OIDC Claim Sub found or ID token missing in /whoami')
        return 'No OIDC Claim Sub found or ID token missing', 404, \
               {'X-Error': 'OIDC Claim Not Found'}

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.oidc_claim_sub == oidc_claim_sub)

        query_result = query.all()

        if len(query_result) == 0:
            # create a new FabricPerson in db, fill in information from the claim sub
            utils.create_new_fabric_person_from_token(request.headers)
            # re-query after insertion
            query = session.query(FabricPerson).filter(FabricPerson.oidc_claim_sub == oidc_claim_sub)
            query_result = query.all()
            if len(query_result) != 1:
                log.error('Unable to insert new user into UIS database in /whoami')
                return 'Insertion in UIS database failed', 500, \
                       {'X-Error': 'Internal server error'}
        else:
            if len(query_result) > 1:
                log.warn(f'Duplicate ODIC claim found in the database {str(oidc_claim_sub)} in /whoami')
                return 'Duplicate OIDC Claim Found: {0}'.format(str(oidc_claim_sub)), 500, \
                       {'X-Error': 'Duplicate person found'}

        person = query_result[0]
        # check with COmanage they are an active user
        status, active_flag, co_person_id = utils.comanage_check_active_person(person)
        if status != 200:
            log.error(f'Error {status} contacting comanage in /whoami')
            return f'Error {status} contacting COmanage', 500, \
                       {'X-Error': 'COmanage problem'}
        commit_needed = False
        if co_person_id is not None and \
                (person.co_person_id is None or len(person.co_person_id) == 0):
            # write Id to the database if we didn't have it and got it now
            setattr(person, 'co_person_id', co_person_id)
            commit_needed = True

        if not active_flag:
            log.warn(f'User co_person_id={co_person_id} is not an active user in /whoami')
            return 'User not an active user', 401, \
                   {'X-Error': 'Unauthorized'}

        # sometimes we don't get a name from the token
        # so get it from COmanage
        if person.name is None or len(person.name) == 0:
            code, name = utils.comanage_get_person_name(co_person_id)
            if name is not None:
                setattr(person, 'name', name)
                commit_needed = True

        if commit_needed:
            session.commit()

        return utils.fill_people_long_from_person(person)
    finally:
        session.close()


def people_uuid_get(uuid):  # noqa: E501
    """person details by UUID
    Person details by UUID # noqa: E501
    :param uuid: People identifier as UUID
    :type uuid: str
    :rtype: PeopleLong
    """
    uuid = str(uuid).strip()
    if not utils.validate_uuid_by_oidc_claim(request.headers, uuid):
        log.error(f'OIDC Claim Sub doesnt match uuid {uuid} in /people/uuid')
        return "OIDC Claim Sub doesnt match UUID", 401, \
               {'X-Error': 'Authorization information is missing or invalid'}

    session = Session()
    query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

    query_result = query.all()

    if len(query_result) == 0:
        log.warn(f'Person UUID {uuid} not found in /people/uuid')
        return 'Person UUID not found: {0}'.format(str(uuid)), 404, \
               {'X-Error': 'People Not Found'}

    if len(query_result) > 1:
        log.warn(f'Duplicate UUID {uuid} found in /people/uuid')
        return 'Duplicate UUID Found: {0}'.format(str(uuid)), 500, \
               {'X-Error': 'Duplicate person found'}

    person = query_result[0]

    return utils.fill_people_long_from_person(person)


def uuid_oidc_claim_sub_get(oidc_claim_sub):
    """
    get the UUID mapped to this claim sub (open to any valid user)
    """
    oidc_claim_sub = str(oidc_claim_sub).strip()

    session = Session()
    status, active_flag = utils.check_user_active(session, request.headers)
    if status != 200:
        log.error(f'Error {status} contacting COmanage in /uuid/oidc_claim_sub')
        return f'Error {status} contacting COmanage', 500, \
               {'X-Error': 'COmanage problem'}
    if not active_flag:
        log.warn(f'User is not an active user in /uuid/oidc_claim_sub')
        return 'User not an active user', 401, \
               {'X-Error': 'Unauthorized'}

    query = session.query(FabricPerson).filter(FabricPerson.oidc_claim_sub == oidc_claim_sub)
    query_result = query.all()

    if len(query_result) == 0:
        log.warn(f'Person with OIDC Claim sub {str(oidc_claim_sub)} in /uuid/oidc_claim_sub not found in database')
        return 'Person with OIDC claim sub not found: {0}'.format(oidc_claim_sub), 404, \
               {'X-Error': 'People Not Found'}
    else:
        if len(query_result) > 1:
            log.warn(f'Duplicate OIDC Claim {str(oidc_claim_sub)} found in the database in /uuid/oidc_claim_sub')
            return 'Duplicate OIDC Claim Found: {0}'.format(oidc_claim_sub), 500, \
                   {'X-Error': 'Duplicate person found'}

    person = query_result[0]
    return person.uuid
