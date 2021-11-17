import connexion
import six

from swagger_server.models.ssh_key_bastion import SshKeyBastion  # noqa: E501
from swagger_server.models.ssh_key_long import SshKeyLong  # noqa: E501
from swagger_server.models.ssh_key_pair import SshKeyPair  # noqa: E501
from swagger_server.models.ssh_key_type import SshKeyType  # noqa: E501
import swagger_server.response_code.sshkey_controller as sc


def bastionkeys_get(secret, since_date):  # noqa: E501
    """Get a list of bastion keys that were created, deactivated or expired since specified date in UTC (open to Bastion hosts)

     # noqa: E501

    :param secret: 
    :type secret: str
    :param since_date: 
    :type since_date: str

    :rtype: List[SshKeyBastion]
    """
    return sc.bastionkeys_get(secret, since_date)


def sshkey_keyid_delete(keyid):  # noqa: E501
    """Delete a specified key based on key UUID (open only to self)

     # noqa: E501

    :param keyid: 
    :type keyid: str

    :rtype: str
    """
    return sc.sshkeys_keyid_delete(keyid)


def sshkey_keyid_get(keyid):  # noqa: E501
    """get metadata, including expiration date for this key based on key UUID (open only to self)

     # noqa: E501

    :param keyid: 
    :type keyid: str

    :rtype: SshKeyLong
    """
    return sc.sshkey_keyid_get(keyid)


def sshkey_keytype_post(keytype, public_openssh, description):  # noqa: E501
    """Add a user-provided ssh public key of specified type. (open only to self)

     # noqa: E501

    :param keytype: 
    :type keytype: dict | bytes
    :param public_openssh: 
    :type public_openssh: str
    :param description: 
    :type description: str

    :rtype: str
    """
    if connexion.request.is_json:
        keytype = SshKeyType.from_dict(connexion.request.get_json())  # noqa: E501
    return sc.sshkeys_keytype_post(keytype, public_openssh, description)


def sshkey_keytype_put(keytype, comment, description):  # noqa: E501
    """Generate a new SSH key of specified type. Return both public and private portions. (open only to self)

     # noqa: E501

    :param keytype: 
    :type keytype: dict | bytes
    :param comment: 
    :type comment: str
    :param description: 
    :type description: str

    :rtype: SshKeyPair
    """
    if connexion.request.is_json:
        keytype = SshKeyType.from_dict(connexion.request.get_json())  # noqa: E501
    return sc.sshkeys_keytype_put(keytype, comment, description)


def sshkey_uuid_keyid_get(uuid, keyid):  # noqa: E501
    """Get a specific key of a given user (open to any valid user)

     # noqa: E501

    :param uuid: 
    :type uuid: str
    :param keyid: 
    :type keyid: str

    :rtype: List[SshKeyLong]
    """
    return sc.sshkey_uuid_keyid_get(uuid, keyid)


def sshkeys_get():  # noqa: E501
    """Get a list of all active/non-expired keys of this user (open to self)

     # noqa: E501


    :rtype: List[SshKeyLong]
    """
    return sc.sshkeys_get()
