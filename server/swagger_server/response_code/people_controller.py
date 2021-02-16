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

from swagger_server.database import Session
from swagger_server.database.models import FabricPerson
from swagger_server.models.people_long import PeopleLong  # noqa: E501
from swagger_server import QUERY_CHARACTER_MIN
import swagger_server.response_code.utils as utils


def people_get(person_name=None):  # noqa: E501
    """list of people
    List of people # noqa: E501
    :param person_name: Search People by Name (ILIKE)
    :type person_name: str
    :rtype: List[PeopleShort]
    """
    person_name = str(person_name).strip()

    # can't let them query by fewer than 5 characters
    if not person_name or len(person_name) < QUERY_CHARACTER_MIN:
        return "Must provide more information", 400, \
               {'X-Error': 'Bad request'}

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            return f'Error {status} contacting COmanage', 500, \
                   {'X-Error': 'COmanage problem'}
        if not active_flag:
            return 'User not an active user', 401, \
                   {'X-Error': 'Unauthorized'}
        query = session.query(FabricPerson).\
            filter(FabricPerson.name.ilike("%{}%".format(str(person_name))))

        query_result = query.all()

        if len(query_result) == 0:
            return 'People Not Found.', 404, {'X-Error': 'People Not Found'}

        response = []
        # TODO: fix pagination
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
                return 'Insertion in UIS database failed', 500, \
                       {'X-Error': 'Internal server error'}
        else:
            if len(query_result) > 1:
                return 'Duplicate OIDC Claim Found: {0}'.format(str(oidc_claim_sub)), 500, \
                       {'X-Error': 'Duplicate person found'}

        person = query_result[0]
        # check with COmanage they are an active user
        status, active_flag, co_person_id = utils.comanage_check_active_person(person)
        if status != 200:
            return f'Error {status} contacting COmanage', 500, \
                       {'X-Error': 'COmanage problem'}
        if co_person_id is not None:
            # write Id to the database if we got it
            setattr(person, 'co_person_id', co_person_id)
            session.commit()

        if not active_flag:
            return 'User not an active user', 401, \
                   {'X-Error': 'Unauthorized'}

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
        return "OIDC Claim Sub doesnt match UUID", 401, \
               {'X-Error': 'Authorization information is missing or invalid'}

    session = Session()
    query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

    query_result = query.all()

    if len(query_result) == 0:
        return 'Person UUID not found: {0}'.format(str(uuid)), 404, \
               {'X-Error': 'People Not Found'}

    if len(query_result) > 1:
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
        return f'Error {status} contacting COmanage', 500, \
               {'X-Error': 'COmanage problem'}
    if not active_flag:
        return 'User not an active user', 401, \
               {'X-Error': 'Unauthorized'}

    query = session.query(FabricPerson).filter(FabricPerson.oidc_claim_sub == oidc_claim_sub)
    query_result = query.all()

    if len(query_result) == 0:
        return 'Person UUID not found: {0}'.format(oidc_claim_sub), 404, \
               {'X-Error': 'People Not Found'}
    else:
        if len(query_result) > 1:
            return 'Duplicate OIDC Claim Found: {0}'.format(oidc_claim_sub), 500, \
                   {'X-Error': 'Duplicate person found'}

    person = query_result[0]
    return person.uuid
