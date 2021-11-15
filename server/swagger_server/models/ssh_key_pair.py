# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class SshKeyPair(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, private_openssh: str=None, public_openssh: str=None):  # noqa: E501
        """SshKeyPair - a model defined in Swagger

        :param private_openssh: The private_openssh of this SshKeyPair.  # noqa: E501
        :type private_openssh: str
        :param public_openssh: The public_openssh of this SshKeyPair.  # noqa: E501
        :type public_openssh: str
        """
        self.swagger_types = {
            'private_openssh': str,
            'public_openssh': str
        }

        self.attribute_map = {
            'private_openssh': 'private_openssh',
            'public_openssh': 'public_openssh'
        }
        self._private_openssh = private_openssh
        self._public_openssh = public_openssh

    @classmethod
    def from_dict(cls, dikt) -> 'SshKeyPair':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The SshKeyPair of this SshKeyPair.  # noqa: E501
        :rtype: SshKeyPair
        """
        return util.deserialize_model(dikt, cls)

    @property
    def private_openssh(self) -> str:
        """Gets the private_openssh of this SshKeyPair.


        :return: The private_openssh of this SshKeyPair.
        :rtype: str
        """
        return self._private_openssh

    @private_openssh.setter
    def private_openssh(self, private_openssh: str):
        """Sets the private_openssh of this SshKeyPair.


        :param private_openssh: The private_openssh of this SshKeyPair.
        :type private_openssh: str
        """

        self._private_openssh = private_openssh

    @property
    def public_openssh(self) -> str:
        """Gets the public_openssh of this SshKeyPair.


        :return: The public_openssh of this SshKeyPair.
        :rtype: str
        """
        return self._public_openssh

    @public_openssh.setter
    def public_openssh(self, public_openssh: str):
        """Sets the public_openssh of this SshKeyPair.


        :param public_openssh: The public_openssh of this SshKeyPair.
        :type public_openssh: str
        """

        self._public_openssh = public_openssh