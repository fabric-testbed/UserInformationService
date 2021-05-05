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
from flask import request

from http import HTTPStatus
from fss_utils.http_errors import cors_response

from swagger_server import log
from swagger_server.database import Session
from swagger_server.models.preferences import Preferences
from swagger_server.database.models import FabricPerson, PreferenceType
import swagger_server.response_code.utils as utils
from swagger_server.response_code.utils import log


OKRETURN = "OK"


def preferences_preftype_uuid_get(preftype, uuid):  # noqa: E501
    """
    Get user preferences as a string from the database
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    uuid = str(uuid).strip()
    if not utils.validate_uuid_by_oidc_claim(request.headers, uuid):
        log.error(f'OIDC Claim Sub doesnt match UUID {uuid} in /preferences/preftype/uuid')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='OIDC Claim Sub doesnt match UUID')

    # get preference by type
    if preftype not in PreferenceType.__members__.keys():
        log.warn(f'Inavlid preference type {str(preftype)} in /preferences/preftype/uuid')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror='Invalid parameter')

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

        query_result = query.all()

        if len(query_result) == 0:
            log.warn(f'Person UUID {uuid} not found in /preferences/preftype/uuid')
            return cors_response(HTTPStatus.NOT_FOUND,
                                 xerror='Person UUID not found: {0}'.format(uuid))

        if len(query_result) > 1:
            log.warn(f"Duplicate UUID {uuid} detected in /preferences/preftype/uuid")
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror='Duplicate UUID Found: {0}'.format(uuid))

        if getattr(query_result[0], preftype) is not None:
            response = json.loads(getattr(query_result[0], preftype))
        else:
            log.warn(f'Preferences {preftype} not found for UUID {uuid}')
            return cors_response(HTTPStatus.NO_CONTENT,
                                 xerror='Preference {0} for UUID {1} not found'.format(preftype, uuid))

        if not isinstance(response, dict):
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror='DB return not a JSON dictionary as preference')

        return response
    finally:
        session.close()


def preferences_preftype_uuid_put(uuid, preftype, preferences=None):  # noqa: E501
    """
    Set user preferences as a string in the database
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    uuid = str(uuid).strip()
    if not utils.validate_uuid_by_oidc_claim(request.headers, uuid):
        log.error(f'OIDC Claim Sub doesnt match UUID {uuid} in /preferences/preftype/uuid')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='OIDC Claim Sub doesnt match UUID')

    # put preference by type
    if preftype not in PreferenceType.__members__.keys():
        log.warn(f'Inavlid preference type {str(preftype)} in /preferences/preftype/uuid')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror='Invalid preference type {0}'.format(str(preftype)))

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

        query_result = query.all()

        if len(query_result) == 0:
            log.warn(f'Person UUID {uuid} not found in /preferences/preftype/uuid')
            return cors_response(HTTPStatus.NOT_FOUND,
                                 xerror='Person UUID Not Found: {0}'.format(uuid))

        if len(query_result) > 1:
            log.warn(f'Duplicate UUID {uuid} not found in /preferences/preftype/uuid')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror='Duplicate UUID Found: {0}'.format(uuid))

        person = query_result[0]

        setattr(person, preftype, json.dumps(preferences))

        session.commit()

        return OKRETURN
    finally:
        session.close()


def preferences_uuid_get(uuid):  # noqa: E501
    """
    Get all user preferences as a single object
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    uuid = str(uuid).strip()
    if not utils.validate_uuid_by_oidc_claim(request.headers, uuid):
        log.error(f'OIDC Claim Sub doesnt match UUID {uuid} in /preferences/uuid')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='OIDC Claim Sub doesnt match UUID')

    session = Session()
    try:
        query = session.query(FabricPerson).filter(FabricPerson.uuid == uuid)

        query_result = query.all()

        if len(query_result) == 0:
            log.warn(f'Person UUID {uuid} not found in /preferences/uuid')
            return cors_response(HTTPStatus.NOT_FOUND,
                                 xerror='Person UUID Not Found: {0}'.format(uuid))

        if len(query_result) > 1:
            log.warn(f'Duplicate UUID {uuid} not found in /preferences/uuid')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror='Duplicate UUID Found: {0}'.format(uuid))

        person = query_result[0]

        response = Preferences(settings=utils.dict_from_json_handle_none(person.settings),
                               permissions=utils.dict_from_json_handle_none(person.permissions),
                               interests=utils.dict_from_json_handle_none(person.interests))
        return response
    finally:
        session.close()
