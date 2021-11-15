import connexion
import six

from swagger_server.models.ssh_key_bastion import SshKeyBastion  # noqa: E501
from swagger_server.models.ssh_key_long import SshKeyLong  # noqa: E501
from swagger_server.models.ssh_key_pair import SshKeyPair  # noqa: E501
from swagger_server.models.ssh_key_short import SshKeyShort  # noqa: E501
from swagger_server.models.ssh_key_type import SshKeyType  # noqa: E501
import swagger_server.response_code.sshkey_controller as sc


def keylist_get(secret, since_date):  # noqa: E501
    """Get a list of keys that were created, deactivated or expired since specified date in UTC (open to Bastion host)

     # noqa: E501

    :param secret: 
    :type secret: str
    :param since_date: 
    :type since_date: str

    :rtype: List[SshKeyBastion]
    """
    return sc.keylist_date_get(secret, since_date)


def sshkeys_keytype_uuid_get(keytype, uuid):  # noqa: E501
    """Get a list of active/non-expired keys of specified type (open to any valid user)

     # noqa: E501

    :param keytype: 
    :type keytype: dict | bytes
    :param uuid: 
    :type uuid: str

    :rtype: List[SshKeyShort]
    """
    if connexion.request.is_json:
        keytype = SshKeyType.from_dict(connexion.request.get_json())  # noqa: E501
    return sc.sshkeys_keytype_uuid_get(keytype, uuid)


def sshkeys_keytype_uuid_keyid_delete(keytype, uuid, keyid):  # noqa: E501
    """Delete a specified key based on key UUID (open only to self)

     # noqa: E501

    :param keytype: 
    :type keytype: dict | bytes
    :param uuid: 
    :type uuid: str
    :param keyid: 
    :type keyid: str

    :rtype: str
    """
    if connexion.request.is_json:
        keytype = SshKeyType.from_dict(connexion.request.get_json())  # noqa: E501
    return sc.sshkeys_keytype_uuid_keyid_delete(keytype, uuid, keyid)


def sshkeys_keytype_uuid_keyid_get(keytype, uuid, keyid):  # noqa: E501
    """get metadata, including expiration date for this key based on key UUID (open only to self)

     # noqa: E501

    :param keytype: 
    :type keytype: dict | bytes
    :param uuid: 
    :type uuid: str
    :param keyid: 
    :type keyid: str

    :rtype: SshKeyLong
    """
    if connexion.request.is_json:
        keytype = SshKeyType.from_dict(connexion.request.get_json())  # noqa: E501
    return sc.sshkeys_keytype_uuid_keyid_get(keytype, uuid, keyid)


def sshkeys_keytype_uuid_post(keytype, uuid, public_openssh):  # noqa: E501
    """Add a user-provided ssh public key of specified type. key_uuid field in SshKeyShort is ignored (open only to self)

     # noqa: E501

    :param keytype: 
    :type keytype: dict | bytes
    :param uuid: 
    :type uuid: str
    :param public_openssh: 
    :type public_openssh: str

    :rtype: str
    """
    if connexion.request.is_json:
        keytype = SshKeyType.from_dict(connexion.request.get_json())  # noqa: E501
    return sc.sshkeys_keytype_uuid_post(keytype, uuid, public_openssh)


def sshkeys_keytype_uuid_put(keytype, uuid, comment, description):  # noqa: E501
    """Generate a new SSH key of specified type. Return both public and private portions. key_uuid field in SshKeyShort is ignored. (open only to self)

     # noqa: E501

    :param keytype: 
    :type keytype: dict | bytes
    :param uuid: 
    :type uuid: str
    :param comment: 
    :type comment: str
    :param description: 
    :type description: str

    :rtype: SshKeyPair
    """
    if connexion.request.is_json:
        keytype = SshKeyType.from_dict(connexion.request.get_json())  # noqa: E501
    return sc.sshkeys_keytype_uuid_put(keytype, uuid, comment, description)
