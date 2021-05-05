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

from swagger_server.models.author_id import AuthorId
from swagger_server.models.author_id_type import AuthorIdType
from flask import request

from http import HTTPStatus
from fss_utils.http_errors import cors_response

import swagger_server.response_code.utils as utils


def authorids_idtype_uuid_get(idtype, uuid):  # noqa: E501

    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    return 'Method unimplemented', 400, {'X-Error': 'Method unimplemented'}


def authorids_idtype_uuid_put(idtype, uuid, idval):  # noqa: E501

    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    return 'Method unimplemented', 400, {'X-Error': 'Method unimplemented'}


def authorids_uuid_get(uuid):  # noqa: E501

    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    return 'Method unimplemented', 400, {'X-Error': 'Method unimplemented'}