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
    if not utils.validate_person(request.headers):
        return "Not a valid FABRIC person", 401, \
               {'X-Error': 'Authorization information is missing or invalid'}

    # can't let them query by fewer than 5 characters
    if not person_name or len(person_name) < QUERY_CHARACTER_MIN:
        return "Must provide more information", 400, \
               {'X-Error': 'Bad request'}

    session = Session()
    try:
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


def people_oidc_claim_sub_get(oidc_claim_sub):  # noqa: E501
    """person details by OIDC Claim sub
    Person details by OIDC Claim sub # noqa: E501
    :param oidc_claim_sub: Search People by OIDC Claim sub (exact match only)
    :type oidc_claim_sub: str
    :rtype: PeopleLong
    """
    oidc_claim_sub = str(oidc_claim_sub).strip()
    if not utils.validate_oidc_claim(request.headers, oidc_claim_sub):
        return "OIDC Claim Sub doesnt match", 401, \
               {'X-Error': 'Authorization information is missing or invalid'}

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.oidc_claim_sub == oidc_claim_sub)

        query_result = query.all()

        if len(query_result) == 0:
            # create a new FabricPerson in db, fill in information from the claim sub
            # and returns a PeopleLong (don't check uniqueness - we just did)
            pl = utils.create_new_fabric_person(request.headers)
            return pl
        else:
            if len(query_result) > 1:
                return 'Duplicate OIDC Claim Found: {0}'.format(str(oidc_claim_sub)), 500, \
                       {'X-Error': 'Duplicate person found'}

        person = query_result[0]
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
    if not utils.validate_person(request.headers):
        return "Not a valid FABRIC person", 401, \
               {'X-Error': 'Authorization information is missing or invalid'}

    session = Session()
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
