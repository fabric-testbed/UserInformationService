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

from typing import List

from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from flask import request
from uuid import uuid4

from fss_utils.http_errors import cors_response
from fss_utils.sshkey import FABRICSSHKey, FABRICSSHKeyException

from swagger_server import SSH_KEY_STORAGE, SSH_KEY_ALGORITHM, SSH_BASTION_KEY_VALIDITY_DAYS, \
    SSH_GARBAGE_COLLECT_AFTER_DAYS, SSH_KEY_SECRET, co_api
from swagger_server.database import Session

import swagger_server.response_code.utils as utils
from swagger_server.response_code.utils import log

from swagger_server.database.models import DbSshKey, FabricPerson

from swagger_server.models.ssh_key_bastion import SshKeyBastion  # noqa: E501
from swagger_server.models.ssh_key_long import SshKeyLong  # noqa: E501
from swagger_server.models.ssh_key_pair import SshKeyPair  # noqa: E501
from swagger_server.models.ssh_key_short import SshKeyShort  # noqa: E501


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
    if SSH_KEY_STORAGE == 'local':
        session = Session()
        try:
            _expire_keys(session)
            _garbage_collect_keys(session)
            # first a list of new keys
            try:
                pdate = datetime.fromisoformat(since_date)
            except ValueError:
                log.error(f'Unable to convert date {since_date}')
                return cors_response(HTTPStatus.BAD_REQUEST,
                                     xerror=f'Provided date {since_date} is invalid.')

            ret = list()
            query = session.query(DbSshKey, FabricPerson).filter(DbSshKey.active == True,
                                                            DbSshKey.created_on > pdate,
                                                            DbSshKey.type == 'bastion',
                                                            DbSshKey.owner_uuid == FabricPerson.uuid)
            query_result = query.all()
            for qk, qp in query_result:
                k = SshKeyBastion()
                k.status = 'active'
                k.public_openssh = " ".join([qk.name, qk.public_key, qk.comment])
                k.login = qp.bastion_login
                ret.append(k)

            query = session.query(DbSshKey, FabricPerson).filter(DbSshKey.active == False,
                                                                DbSshKey.deactivated_on > pdate,
                                                                 DbSshKey.type == 'bastion',
                                                                DbSshKey.owner_uuid == FabricPerson.uuid)
            query_result = query.all()
            for qk, qp in query_result:
                k = SshKeyBastion()
                k.status = 'deactivated'
                k.public_openssh = " ".join([qk.name, qk.public_key, qk.comment])
                k.login = qp.bastion_login
                ret.append(k)

            return ret
        finally:
            session.commit()
            session.close()
    else:
        raise RuntimeError('COmanage backend not yet implemented')


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

    if SSH_KEY_STORAGE == 'local':
        session = Session()
        try:
            _expire_keys(session)
            _garbage_collect_keys(session)

            query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                                   DbSshKey.active == True)
            query_result = query.all()

            ret = list()
            for res in query_result:
                ret.append(_fill_long_key(query_result[0]))

            return ret
        finally:
            session.commit()
            session.close()
    else:
        raise RuntimeError('COmanage not yet implemented')


def sshkeys_keyid_delete(keyid: str) -> str:  # noqa: E501
    """
    Delete/deactivate a specified key. Open only to self.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    _uuid = utils.get_uuid_by_oidc_claim(request.headers)

    if _uuid is None:
        log.error(f'OIDC Claim Sub is invalid or unable to find UUID {_uuid} in sshkeys_keyid_delete')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='Unable to find UUID from OIDC Sub claim')

    if SSH_KEY_STORAGE == 'local':
        session = Session()
        try:
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
    else:
        raise RuntimeError('COmanage not yet implemented')


def sshkey_uuid_keyid_get(_uuid: str, keyid: str) -> SshKeyLong:  # noqa: E501
    """
    Get a specified active key for this user. Open to any valid user.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    _uuid = _uuid.strip()

    if SSH_KEY_STORAGE == 'local':
        session = Session()
        try:
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
    else:
        raise RuntimeError('COmanage not yet implemented')


def sshkey_keyid_get(keyid: str) -> SshKeyLong:  # noqa: E501
    """
    Get a specified key regardless of status. Open only to self.
    """
    if not utils.any_authenticated_user(request.headers):
        return cors_response(HTTPStatus.UNAUTHORIZED,
                             xerror='User not authenticated')

    _uuid = utils.get_uuid_by_oidc_claim(request.headers)

    if _uuid is None:
        log.error(f'OIDC Claim Sub is invalid or unable to find UUID {_uuid} in sshkeys_keyid_get')
        return cors_response(HTTPStatus.FORBIDDEN,
                             xerror='Unable to find UUID from OIDC Sub claim')

    if SSH_KEY_STORAGE == 'local':
        session = Session()
        try:
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
    else:
        raise RuntimeError('COmanage not yet implemented')


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

    try:
        # instantiate to test its validity
        fssh = FABRICSSHKey(public_openssh)
    except FABRICSSHKeyException as e:
        log.error(f'Provided key for {_uuid} is invalid due to {str(e)}')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror=f'Provided key for {_uuid} is invalid due to {str(e)}')

    short_key = SshKeyShort()
    short_key.name = fssh.name
    short_key.comment = fssh.comment
    short_key.public_key = fssh.public_key
    short_key.fingerprint = fssh.get_fingerprint()
    short_key.description = description

    if not _check_unique(_uuid, short_key.fingerprint):
        log.error(f'Provided key for {_uuid} with fingerprint {short_key.fingerprint} is not unique')
        return cors_response(HTTPStatus.BAD_REQUEST,
                             xerror=f'Provided key for {_uuid} with fingerprint {short_key.fingerprint} is not unique')

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
    short_key.description = description
    short_key.fingerprint = fssh.get_fingerprint()
    # insert in database
    _store_ssh_key(_uuid, keytype, short_key)

    ret = fssh.as_keypair()

    # return to user the keypair
    return SshKeyPair(ret[0], ret[1])


def _expire_keys(session=None):
    """
    Scan the keys and deactivate those that are expired.
    """
    if SSH_KEY_STORAGE == 'local':
        now = datetime.now(timezone.utc)
        query = session.query(DbSshKey).filter(DbSshKey.expires_on < now,
                                               DbSshKey.active == True)
        query_result = query.all()
        log.info(f'Expiring {len(query.all())} keys')
        for q in query_result:
            q.deactivated_on = now
            q.deactivation_reason = f'Key automatically expired on {now}Z'
            q.active = False
    else:
        raise RuntimeError('COmanage backend not yet implemented')


def _garbage_collect_keys(session=None):
    """
    Delete deactivated keys older than specified period
    """
    if SSH_KEY_STORAGE == 'local':
        now = datetime.now(timezone.utc)
        gc_delta = timedelta(minutes=SSH_GARBAGE_COLLECT_AFTER_DAYS)
        check_instant = now - gc_delta
        session.query(DbSshKey).filter(DbSshKey.deactivated_on < check_instant,
                                       DbSshKey.active == False).delete()
    else:
        raise RuntimeError('COmanage backend not yet implemented')


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
        skl.deactivated_on = query_result.deactivated_on
        skl.deactivation_reason = query_result.deactivation_reason
    return skl


def _store_ssh_key(_uuid: str, keytype:str, key: SshKeyShort) -> None:
    """
    Select where to store the ssh key - locally or in COmanage.
    """

    if SSH_KEY_STORAGE == 'local':
        log.debug(f'Storing key {key.name} locally')
        _store_ssh_key_local(_uuid, keytype, key)
    else:
        log.debug(f'Storing key {key.name} in COmanage')
        _store_ssh_key_comanage(_uuid, keytype, key)


def _store_ssh_key_local(_uuid: str, keytype: str, key: SshKeyShort) -> None:
    """
    Store SSH key in the database
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
        session.add(db_key)
        session.commit()
    finally:
        session.close()


def _store_ssh_key_comanage(_uuid: str, keytype: str, key: SshKeyShort) -> None:

    pass


def _check_unique(_uuid: str, fingerprint: str) -> bool:
    """
    See if a key with this fingerprint is already in the system for this user,
    regardless of type or status.
    """
    session = Session()
    try:
        query = session.query(DbSshKey).filter(DbSshKey.owner_uuid == _uuid,
                                               DbSshKey.fingerprint == fingerprint)
        query_result = query.all()
        if len(query_result) > 0:
            return False
        return True

    finally:
        session.close()
