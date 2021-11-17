# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class SshKeyShort(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, key_uuid: str=None, name: str=None, comment: str=None, description: str=None, fingerprint: str=None, public_key: str=None):  # noqa: E501
        """SshKeyShort - a model defined in Swagger

        :param key_uuid: The key_uuid of this SshKeyShort.  # noqa: E501
        :type key_uuid: str
        :param name: The name of this SshKeyShort.  # noqa: E501
        :type name: str
        :param comment: The comment of this SshKeyShort.  # noqa: E501
        :type comment: str
        :param description: The description of this SshKeyShort.  # noqa: E501
        :type description: str
        :param fingerprint: The fingerprint of this SshKeyShort.  # noqa: E501
        :type fingerprint: str
        :param public_key: The public_key of this SshKeyShort.  # noqa: E501
        :type public_key: str
        """
        self.swagger_types = {
            'key_uuid': str,
            'name': str,
            'comment': str,
            'description': str,
            'fingerprint': str,
            'public_key': str
        }

        self.attribute_map = {
            'key_uuid': 'key_uuid',
            'name': 'name',
            'comment': 'comment',
            'description': 'description',
            'fingerprint': 'fingerprint',
            'public_key': 'public_key'
        }
        self._key_uuid = key_uuid
        self._name = name
        self._comment = comment
        self._description = description
        self._fingerprint = fingerprint
        self._public_key = public_key

    @classmethod
    def from_dict(cls, dikt) -> 'SshKeyShort':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The SshKeyShort of this SshKeyShort.  # noqa: E501
        :rtype: SshKeyShort
        """
        return util.deserialize_model(dikt, cls)

    @property
    def key_uuid(self) -> str:
        """Gets the key_uuid of this SshKeyShort.


        :return: The key_uuid of this SshKeyShort.
        :rtype: str
        """
        return self._key_uuid

    @key_uuid.setter
    def key_uuid(self, key_uuid: str):
        """Sets the key_uuid of this SshKeyShort.


        :param key_uuid: The key_uuid of this SshKeyShort.
        :type key_uuid: str
        """

        self._key_uuid = key_uuid

    @property
    def name(self) -> str:
        """Gets the name of this SshKeyShort.


        :return: The name of this SshKeyShort.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """Sets the name of this SshKeyShort.


        :param name: The name of this SshKeyShort.
        :type name: str
        """

        self._name = name

    @property
    def comment(self) -> str:
        """Gets the comment of this SshKeyShort.


        :return: The comment of this SshKeyShort.
        :rtype: str
        """
        return self._comment

    @comment.setter
    def comment(self, comment: str):
        """Sets the comment of this SshKeyShort.


        :param comment: The comment of this SshKeyShort.
        :type comment: str
        """

        self._comment = comment

    @property
    def description(self) -> str:
        """Gets the description of this SshKeyShort.


        :return: The description of this SshKeyShort.
        :rtype: str
        """
        return self._description

    @description.setter
    def description(self, description: str):
        """Sets the description of this SshKeyShort.


        :param description: The description of this SshKeyShort.
        :type description: str
        """

        self._description = description

    @property
    def fingerprint(self) -> str:
        """Gets the fingerprint of this SshKeyShort.


        :return: The fingerprint of this SshKeyShort.
        :rtype: str
        """
        return self._fingerprint

    @fingerprint.setter
    def fingerprint(self, fingerprint: str):
        """Sets the fingerprint of this SshKeyShort.


        :param fingerprint: The fingerprint of this SshKeyShort.
        :type fingerprint: str
        """

        self._fingerprint = fingerprint

    @property
    def public_key(self) -> str:
        """Gets the public_key of this SshKeyShort.


        :return: The public_key of this SshKeyShort.
        :rtype: str
        """
        return self._public_key

    @public_key.setter
    def public_key(self, public_key: str):
        """Sets the public_key of this SshKeyShort.


        :param public_key: The public_key of this SshKeyShort.
        :type public_key: str
        """

        self._public_key = public_key
