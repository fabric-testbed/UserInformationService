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

import json

from swagger_server import MOCK_SERVICE, log
from swagger_server.database import Session
from swagger_server.models.preferences import Preferences
from swagger_server.database.models import FabricPerson, PreferenceType
from .utils import validate_uuid_by_oidc_claim, dict_from_json_handle_none


OKRETURN = "OK"


def preferences_preftype_uuid_get(preftype, uuid):  # noqa: E501
    """
    Get user preferences as a string from the database
    """
    if MOCK_SERVICE:
        log.info("Mock service enabled, skipping validation")
    else:
        log.info("Validating OIDC claim UUID match")
        if not validate_uuid_by_oidc_claim(uuid):
            log.info("OIDC Claim did not pass validation")
            return "OIDC Claim Sub doesnt match UUID", 401, \
                   {'X-Error': 'Authorization information is missing or invalid'}

    # get preference by type
    if preftype not in PreferenceType.__members__.keys():
        return 'Invalid preference type {0}'.format(str(preftype)), 400, {'X-Error': 'Invalid parameter'}

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

        query_result = query.all()

        if len(query_result) == 0:
            return 'Person UUID not found: {0}'.format(str(uuid)), 404, \
                   {'X-Error': 'People Not Found'}

        if len(query_result) > 1:
            log.warn(f"Duplicate UUID {uuid} detected")
            return 'Duplicate UUID Found: {0}'.format(str(uuid)), 500, {'X-Error': 'Duplicate UUID found'}

        if getattr(query_result[0], preftype) is not None:
            response = json.loads(getattr(query_result[0], preftype))
        else:
            return 'Preference {0} for UUID {1} not found'.format(preftype, str(uuid)), \
                   204, {'X-Error': 'Preference not found'}

        if not isinstance(response, dict):
            return 'Unable to parse object into dict', 500, {'X-Error': 'DB return not a JSON dictionary as preference'}

        return response
    finally:
        session.close()


def preferences_preftype_uuid_put(uuid, preftype, preferences=None):  # noqa: E501
    """
    Set user preferences as a string in the database
    """
    if MOCK_SERVICE:
        log.info("Mock service enabled, skipping validation")
    else:
        log.info("Validating OIDC claim UUID match")
        if not validate_uuid_by_oidc_claim(uuid):
            log.info("OIDC Claim did not pass validation")
            return "OIDC Claim Sub doesnt match UUID", 401, \
                   {'X-Error': 'Authorization information is missing or invalid'}

    # put preference by type
    if preftype not in PreferenceType.__members__.keys():
        return 'Invalid preference type {0}'.format(str(preftype)), 400, {'X-Error': 'Invalid parameter'}

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

        query_result = query.all()

        if len(query_result) == 0:
            return 'Person UUID Not Found: {0}'.format(str(uuid)), 404, {'X-Error': 'Person UUID Not Found'}

        if len(query_result) > 1:
            return 'Duplicate UUID Found: {0}'.format(str(uuid)), 500, {'X-Error': 'Duplicate UUID found'}

        person = query_result[0]

        print(f"SETTING PREFERENCE {preftype} of user {uuid} to {preferences} as {json.dumps(preferences)}")
        setattr(person, preftype, json.dumps(preferences))

        session.commit()

        return OKRETURN
    finally:
        session.close()


def preferences_uuid_get(uuid):  # noqa: E501
    """
    Get all user preferences as a single object
    """
    if MOCK_SERVICE:
        log.info("Mock service enabled, skipping validation")
    else:
        log.info("Validating OIDC claim UUID match")
        if not validate_uuid_by_oidc_claim(uuid):
            log.info("OIDC Claim did not pass validation")
            return "OIDC Claim Sub doesnt match UUID", 401, \
                   {'X-Error': 'Authorization information is missing or invalid'}

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

        query_result = query.all()

        if len(query_result) == 0:
            return 'Person UUID Not Found: {0}'.format(str(uuid)), 404, {'X-Error': 'Person UUID Not Found'}

        if len(query_result) > 1:
            return 'Duplicate UUID Found: {0}'.format(str(uuid)), 500, {'X-Error': 'Duplicate UUID found'}

        person = query_result[0]

        response = Preferences(settings=dict_from_json_handle_none(person.settings),
                               permissions=dict_from_json_handle_none(person.permissions),
                               interests=dict_from_json_handle_none(person.interests))
        return response
    finally:
        session.close()
