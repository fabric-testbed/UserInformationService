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
import enum
from typing import List
from enum import Enum
from dataclasses import dataclass

import re
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

import requests
from flask import request
from uuid import uuid4

from fss_utils.http_errors import cors_response
from fss_utils.sshkey import FABRICSSHKey, FABRICSSHKeyException

from swagger_server import SSH_SLIVER_KEY_TO_COMANAGE, SSH_KEY_ALGORITHM, SSH_BASTION_KEY_VALIDITY_DAYS, \
    SSH_GARBAGE_COLLECT_AFTER_DAYS, SSH_KEY_SECRET, SSH_KEY_QTY_LIMIT, co_api
from swagger_server.database import Session

import swagger_server.response_code.utils as utils
from swagger_server.response_code.utils import log

from swagger_server.database.models import DbSshKey, FabricPerson

from swagger_server.models.ssh_key_bastion import SshKeyBastion  # noqa: E501
from swagger_server.models.ssh_key_long import SshKeyLong  # noqa: E501
from swagger_server.models.ssh_key_pair import SshKeyPair  # noqa: E501


class KeyType(Enum):
    bastion = enum.auto()
    sliver = enum.auto()

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class KeyStatus(Enum):
    active = enum.auto()
    deactivated = enum.auto()

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


@dataclass
class SshKeyShort:
    # name, comment and public key can be stored locally or in COmanage
    name: str
    comment: str
    public_key: str
    # description and fingerprint must be stored locally
    description: str
    fingerprint: str

    def __init__(self, name=None, comment=None, public_key=None, description=None, fingerprint=None):
        self.name = name
        self.comment = comment
        self.public_key = public_key
        self.description = description
        self.fingerprint = fingerprint


TZISO = r"^.+\+[\d]{2}:[\d]{2}$"
TZPYTHON = r"^.+\+[\d]{4}$"
DESCRIPTION_REGEX = r"^[\w\s\-\.@_()/]{5,255}$"
COMMENT_LENGTH = 100


def bastionkeys_get(secret, since_date) -> List[SshKeyBastion]:
    """
    Special endpoint for bastion agent to get a list of
    keys that have been added/deactivated/expired.
    Find bastion keys that were (a) created since _date and
    (b) deactivated since _date.
    """
    if secret != SSH_KEY_SECRET:
        log.error(f'Provided secret {secret} does not match the configured secret for /keylist endpoint')
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authorized')
    session = Session()
    try:
        _expire_keys(session)
        _garbage_collect_keys(session)
        # first a list of new keys
        try:
            # with +00:00
            if re.match(TZISO, since_date) is not None:
                pdate = datetime.fromisoformat(since_date)
            # with +0000
            elif re.match(TZPYTHON, since_date) is not None:
                pdate = datetime.strptime(since_date, "%Y-%m-%d %H:%M:%S%z")
            # perhaps no TZ info? add as if UTC
            else:
                pdate = datetime.strptime(since_date + "+0000", "%Y-%m-%d %H:%M:%S%z")
            # convert to UTC
            pdate = pdate.astimezone(timezone.utc)
        except ValueError:
            log.error(f'Unable to convert date {since_date}')
            return cors_response(HTTPStatus.BAD_REQUEST,
                                 xerror=f'Provided date {since_date} is invalid.')

        ret = list()
        query = session.query(DbSshKey, FabricPerson).filter(DbSshKey.active == True,
                                                             DbSshKey.created_on > pdate,
                                                             DbSshKey.type == KeyType.bastion.name,
                                                             DbSshKey.owner_uuid == FabricPerson.uuid)
        query_result = query.all()
        for qk, qp in query_result:
            try:
                k = SshKeyBastion()
                k.status = KeyStatus.active.name
                # for bastion update the comment to include expiration date/time
                k.public_openssh = " ".join([qk.name, qk.public_key,
                                             _make_bastion_comment(qk.comment, qk.expires_on)])
                k.login = qp.bastion_login
                ret.append(k)
            except Exception:
                log.error(f'Unable to report new bastion key starting with {qk.public_key[0:100]} '
                          f'for user {qp.bastion_login}')

        query = session.query(DbSshKey, FabricPerson).filter(DbSshKey.active == False,
                                                             DbSshKey.deactivated_on > pdate,
                                                             DbSshKey.type == KeyType.bastion.name,
                                                             DbSshKey.owner_uuid == FabricPerson.uuid)
        query_result = query.all()
        for qk, qp in query_result:
            try:
                k = SshKeyBastion()
                k.status = KeyStatus.deactivated.name
                # for bastion update the comment to include expiration date/time
                k.public_openssh = " ".join([qk.name, qk.public_key,
                                             _make_bastion_comment(qk.comment, qk.expires_on)])
                k.login = qp.bastion_login
                ret.append(k)
            except Exception:
                log.error(f'Unable to report expired bastion key starting with {qk.public_key[0:100]} '
                          f'for user {qp.bastion_login}')

        return ret
    finally:
        session.commit()
        session.close()


def sshkeys_get() -> List[SshKeyLong]:  # noqa: E501
    """
    Get a list of active keys for a given user
    Open to self.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    _uuid = utils.get_uuid_by_oidc_claim(request.headers)

    if _uuid is None:
        log.error(f'OIDC Claim Sub is invalid or unable to find UUID {_uuid} in sshkeys_get')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='Unable to find UUID from OIDC Sub claim')

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            log.error(f'Error {status} contacting COmanage in sshkeys_get')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror=f'Error {status} contacting COmanage')

        if not active_flag:
            log.warn(f'User is not an active user in sshkeys_get')
            return cors_response(HTTPStatus.FORBIDDEN,
                                 xerror='User not an active user')

        _expire_keys(session)
        _garbage_collect_keys(session)

        query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                               DbSshKey.active == True)
        query_result = query.all()

        ret = list()
        for res in query_result:
            ret.append(_fill_long_key(res))

        return ret
    finally:
        session.commit()
        session.close()


def sshkeys_keyid_delete(keyid: str) -> str:  # noqa: E501
    """
    Delete/deactivate a specified key. Open only to self.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    if _bad_uuid(keyid):
        log.error(f'Invalid keyid {keyid} supplied by the caller, rejecting in ssh_keyid_delete.')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror='Supplied keyid {0} is not valid.'.format(keyid))

    _uuid = utils.get_uuid_by_oidc_claim(request.headers)

    if _uuid is None:
        log.error(f'OIDC Claim Sub is invalid or unable to find UUID {_uuid} in sshkeys_keyid_delete')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='Unable to find UUID from OIDC Sub claim')

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            log.error(f'Error {status} contacting COmanage in sshkeys_keyid_delete')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror=f'Error {status} contacting COmanage')

        if not active_flag:
            log.warn(f'User is not an active user in sshkeys_keyid_delete')
            return cors_response(HTTPStatus.FORBIDDEN,
                                 xerror='User not an active user')

        query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                               DbSshKey.key_uuid == keyid,
                                               DbSshKey.active == True)
        query_result = query.all()
        if len(query_result) > 0:
            for q in query_result:
                q.active = False
                q.deactivation_reason = f'Deactivated by owner on {datetime.now(timezone.utc)}Z'
                q.deactivated_on = datetime.now(timezone.utc)
        session.commit()

        return "OK"

    finally:
        session.close()


def sshkey_uuid_keyid_get(_uuid: str, keyid: str) -> SshKeyLong:  # noqa: E501
    """
    Get a specified active key for this user. Open to any valid user.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    _uuid = _uuid.strip()

    if _bad_uuid(_uuid):
        log.error(f'Invalid UUID {_uuid} supplied by the caller, rejecting in sshkey_uuid_keyid_get.')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror='Supplied UUID {0} is not valid.'.format(_uuid))

    if _bad_uuid(keyid):
        log.error(f'Invalid keyid {keyid} supplied by the caller, rejecting in sshkey_uuid_keyid_get.')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror='Supplied keyid {0} is not valid.'.format(keyid))

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            log.error(f'Error {status} contacting COmanage in sshkeys_uuid_keyid_get')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror=f'Error {status} contacting COmanage')

        if not active_flag:
            log.warn(f'User is not an active user in in sshkeys_uuid_keyid_get')
            return cors_response(HTTPStatus.FORBIDDEN,
                                 xerror='User not an active user')

        _expire_keys(session)
        _garbage_collect_keys(session)

        query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                               DbSshKey.active == True,
                                               DbSshKey.key_uuid == keyid)
        query_result = query.all()

        if len(query_result) < 1:
            log.warn(f'Unable to find active key {keyid} for user {_uuid} in sshkeys_uuid_keyid_get, '
                     f'proceeding')
            return cors_response(HTTPStatus.NOT_FOUND,
                                 xerror='Key {0} not found for user {1}'.format(keyid, _uuid))

        return _fill_long_key(query_result[0])

    finally:
        session.commit()
        session.close()


def sshkey_keyid_get(keyid: str) -> SshKeyLong:  # noqa: E501
    """
    Get a specified key regardless of status. Open only to self.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    if _bad_uuid(keyid):
        log.error(f'Invalid keyid {keyid} supplied by the caller, rejecting.')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror='Supplied keyid {0} is not valid.'.format(keyid))

    _uuid = utils.get_uuid_by_oidc_claim(request.headers)

    if _uuid is None:
        log.error(f'OIDC Claim Sub is invalid or unable to find UUID {_uuid} in sshkeys_keyid_get')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='Unable to find UUID from OIDC Sub claim')

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            log.error(f'Error {status} contacting COmanage in sshkeys_keyid_get')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror=f'Error {status} contacting COmanage')

        if not active_flag:
            log.warn(f'User is not an active user in sshkeys_keyid_get')
            return cors_response(HTTPStatus.FORBIDDEN,
                                 xerror='User not an active user')

        _expire_keys(session)
        _garbage_collect_keys(session)

        query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                               DbSshKey.key_uuid == keyid)
        query_result = query.all()

        if len(query_result) < 1:
            log.warn(f'Unable to find key {keyid} for user {_uuid} in sshkeys_keyid_get, '
                     f'proceeding')
            return cors_response(HTTPStatus.NOT_FOUND,
                                 xerror='Key {0} not found for user {1}'.format(keyid, _uuid))

        return _fill_long_key(query_result[0])

    finally:
        session.commit()
        session.close()


def sshkeys_keytype_post(keytype: str, public_openssh: str, description: str) -> str:  # noqa: E501
    """
    Post a public key
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    _uuid = utils.get_uuid_by_oidc_claim(request.headers)

    if _uuid is None:
        log.error(f'OIDC Claim Sub is invalid or unable to find UUID {_uuid} in sshkeys_keytype_post')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='Unable to find UUID from OIDC Sub claim')

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            log.error(f'Error {status} contacting COmanage in sshkeys_keytype_post')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror=f'Error {status} contacting COmanage')

        if not active_flag:
            log.warn(f'User is not an active user in sshkeys_keytype_post')
            return cors_response(HTTPStatus.FORBIDDEN,
                                 xerror='User not an active user')

        # instantiate to test its validity
        fssh = FABRICSSHKey(public_openssh)

        short_key = SshKeyShort()
        short_key.name = fssh.name
        short_key.comment = fssh.comment
        short_key.public_key = fssh.public_key
        short_key.fingerprint = fssh.get_fingerprint()
        matches = re.match(DESCRIPTION_REGEX, description)
        if matches is None:
            log.error(f'Provided description for {_uuid} does not match expected REGEX {DESCRIPTION_REGEX}')
            return cors_response(HTTPStatus.BAD_REQUEST,
                                 xerror=f'Provided description does not match expected REGEX {DESCRIPTION_REGEX}')
        short_key.description = description

        if not _check_unique(_uuid, short_key.fingerprint, session):
            log.error(f'Provided key for {_uuid} with fingerprint {short_key.fingerprint} is not unique')
            return cors_response(HTTPStatus.BAD_REQUEST,
                                 xerror=f'Provided key for {_uuid} with fingerprint '
                                        f'{short_key.fingerprint} is not unique')
        if _check_key_qty(_uuid, keytype, session) >= SSH_KEY_QTY_LIMIT:
            log.error(f'Too many keys of type {keytype} for user {_uuid}, limit {SSH_KEY_QTY_LIMIT}')
            return cors_response(HTTPStatus.BAD_REQUEST,
                                 xerror=f'Too many active keys for this user, limit {SSH_KEY_QTY_LIMIT}')
    except FABRICSSHKeyException as e:
        log.error(f'Provided key for {_uuid} is invalid due to {str(e)}')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror=f'Provided key for {_uuid} is invalid due to {str(e)}')
    finally:
        if session is not None:
            session.close()

    _store_ssh_key(_uuid, keytype, short_key)

    return "OK"


def sshkeys_keytype_put(keytype: str, comment: str, description: str) -> SshKeyPair: # noqa: E501
    """
    Generate a key pair returning it.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    _uuid = utils.get_uuid_by_oidc_claim(request.headers)

    if _uuid is None:
        log.error(f'OIDC Claim Sub is invalid or unable to find UUID {_uuid} in sshkeys_keytype_put')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='Unable to find UUID from OIDC Sub claim')

    session = Session()
    try:
        status, active_flag = utils.check_user_active(session, request.headers)
        if status != 200:
            log.error(f'Error {status} contacting COmanage in sshkeys_keytype_put')
            return cors_response(HTTPStatus.INTERNAL_SERVER_ERROR,
                                 xerror=f'Error {status} contacting COmanage')

        if not active_flag:
            log.warn(f'User is not an active user in sshkeys_keytype_put')
            return cors_response(HTTPStatus.FORBIDDEN,
                                 xerror='User not an active user')
    finally:
        if session is not None:
            session.close()

    log.info(f'Generating key of type {keytype} for {_uuid} with comment {comment}')
    try:
        fssh = FABRICSSHKey.generate(comment, SSH_KEY_ALGORITHM)
    except FABRICSSHKeyException as e:
        log.error(f'Unable to generate a new key for {_uuid} due to {str(e)}')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror=f'Unable to generate a new key for {_uuid} due to {str(e)}')

    short_key = SshKeyShort()
    short_key.name = fssh.name
    short_key.public_key = fssh.public_key
    short_key.comment = fssh.comment
    matches = re.match(DESCRIPTION_REGEX, description)
    if matches is None:
        log.error(f'Provided description for {_uuid} does not match expected REGEX {DESCRIPTION_REGEX}')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror=f'Provided description does not match expected REGEX {DESCRIPTION_REGEX}')
    short_key.description = description
    short_key.fingerprint = fssh.get_fingerprint()
    # insert in database
    _store_ssh_key(_uuid, keytype, short_key)

    ret = fssh.as_keypair()

    # return to user the keypair
    return SshKeyPair(ret[0], ret[1])


def _expire_keys(session):
    """
    Scan the keys and deactivate those that are expired.
    """
    now = datetime.now(timezone.utc)
    query = session.query(DbSshKey).filter(DbSshKey.expires_on < now,
                                           DbSshKey.active == True)
    query_result = query.all()
    log.info(f'Expiring {len(query.all())} keys')
    for q in query_result:
        q.deactivated_on = now
        q.deactivation_reason = f'Key automatically expired on {now}Z'
        q.active = False


def _garbage_collect_keys(session):
    """
    Delete deactivated keys older than specified period (from db and COmanage)
    """
    now = datetime.now(timezone.utc)
    gc_delta = timedelta(minutes=SSH_GARBAGE_COLLECT_AFTER_DAYS)
    check_instant = now - gc_delta
    if SSH_SLIVER_KEY_TO_COMANAGE:
        query = session.query(DbSshKey).filter(DbSshKey.deactivated_on < check_instant,
                                               DbSshKey.active == False,
                                               DbSshKey.type == KeyType.sliver.name)
        query_result = query.all()
        for q in query_result:
            log.info(f'Removing expired sliver key {q.comment}/{q.key_uuid} for user {q.owner_uuid} from COmanage')
            try:
                co_api.ssh_keys_delete(q.comanage_key_id)
            except requests.HTTPError as e:
                log.error(f'Unable to delete expired sliver key {q.key_uuid}/{q.key_uuid} for user {q.owner_uuid} '
                          f'from COmanage due to: {e}')

    session.query(DbSshKey).filter(DbSshKey.deactivated_on < check_instant,
                                   DbSshKey.active == False).delete()


def _fill_long_key(query_result) -> SshKeyLong:

    skl = SshKeyLong()
    skl.name = query_result.name
    skl.description = query_result.description
    skl.comment = query_result.comment
    skl.key_uuid = query_result.key_uuid
    skl.public_key = query_result.public_key
    skl.created_on = str(query_result.created_on)
    skl.expires_on = str(query_result.expires_on)
    skl.fingerprint = query_result.fingerprint
    if not query_result.active:
        skl.deactivated_on = str(query_result.deactivated_on)
        skl.deactivation_reason = query_result.deactivation_reason
    return skl


def _store_ssh_key(_uuid: str, keytype: str, key: SshKeyShort) -> None:
    """
    Select where to store the ssh key - locally or in COmanage.
    """

    db_key = DbSshKey()
    db_key.owner_uuid = _uuid
    db_key.key_uuid = str(uuid4())
    db_key.name = key.name
    db_key.description = key.description
    db_key.comment = key.comment
    db_key.public_key = key.public_key
    db_key.created_on = datetime.now(timezone.utc)
    exp_delta = timedelta(minutes=SSH_BASTION_KEY_VALIDITY_DAYS)
    db_key.expires_on = db_key.created_on + exp_delta
    db_key.active = True
    db_key.fingerprint = key.fingerprint
    # bastion or sliver
    db_key.type = keytype

    session = Session()
    try:
        # did we want to store copy of sliver key in COmanage?
        if SSH_SLIVER_KEY_TO_COMANAGE and keytype == KeyType.sliver.name:
            log.debug(f'Storing sliver key {db_key.comment} for user {_uuid} in COmanage')
            db_key.comanage_key_id = None
            query = session.query(FabricPerson).filter(FabricPerson.uuid == _uuid)
            query_result = query.all()
            if len(query_result) == 0:
                log.error(f'Unable to store key {db_key.comment} for user {_uuid} in COmanage'
                          f' - unable to find them in database')
            else:
                co_key_response = None
                try:
                    person = query_result[0]
                    co_person_id = person.co_person_id
                    if co_person_id is None:
                        log.info(f'Looking up co_person_id in _store_ssh_key for person {person.uuid}')
                        # we already know they are active
                        _, _, co_person_id = utils.comanage_check_active_person(person)

                    if co_person_id is not None:
                        # update the person table in database with co_person_id while we're at it
                        setattr(person, 'co_person_id', co_person_id)
                        log.debug(f'Adding sliver key {db_key.comment} for user {_uuid}/{co_person_id} '
                                  f'to COmanage [ {key.public_key=}, {key.name=}, {key.comment=}')
                        co_key_response = co_api.ssh_keys_add(query_result[0].co_person_id,
                                                     key.public_key, key.name, key.comment)
                    else:
                        log.warn(f'Unable to add sliver key {db_key.comment} for user '
                                 f'{_uuid} due to missing co_person_id')
                except requests.HTTPError as e:
                    log.error(f'Unable to add sliver key {db_key.comment} for user {_uuid} to COmanage due to {e}')
                if co_key_response:
                    if co_key_response.get('Id', None) is None:
                        log.error(f'Unable to add sliver key {db_key.comment} for user '
                                  f'{_uuid} due to unexpected return format of the response: {co_key_response=}')
                    else:
                        db_key.comanage_key_id = co_key_response['Id']

        session.add(db_key)
        session.commit()
    finally:
        session.close()


def _check_key_qty(_uuid: str, keytype: str, session: Session) -> int:
    """
    How many active keys of this type are already there for this user?
    """
    query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                           DbSshKey.active == True,
                                           DbSshKey.type == keytype)
    query_result = query.all()
    return len(query_result)


def _check_unique(_uuid: str, fingerprint: str, session: Session) -> bool:
    """
    See if a key with this fingerprint is already in the system for this user,
    regardless of type or status.
    """
    query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                           DbSshKey.fingerprint == fingerprint)
    query_result = query.all()
    if len(query_result) > 0:
        return False
    return True


def _bad_uuid(_uuid: str) -> bool:
    """
    Check that UUID (user or key) is reasonable.
    """
    # for now just check length. could do regex if we wanted to.
    if len(_uuid) > 64:
        return True
    return False


def _make_bastion_comment(comment: str, expires_on) -> str:
    """
    Return a new comment that is a concatenation of the original comment
    with the expiration date for consumption on bastion hosts.
    """
    # we want to keep the comment under 100 character
    # so we trim the original comment if needed:
    # the date is 23 characters long: _(2021-11-18_10:17:05)_
    # we don't ever want this to fail so someone can't construct
    # a comment so the corresponding key can't be purged
    ts = expires_on.strftime("_(%Y-%m-%d_%H:%M:%S%z)_")
    return comment.strip()[0:COMMENT_LENGTH-len(ts)] + ts