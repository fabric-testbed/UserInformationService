# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.ssh_key_status import SshKeyStatus  # noqa: F401,E501
from swagger_server import util


class SshKeyBastion(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, public_openssh: str=None, login: str=None, gecos: str=None, status: SshKeyStatus=None):  # noqa: E501
        """SshKeyBastion - a model defined in Swagger

        :param public_openssh: The public_openssh of this SshKeyBastion.  # noqa: E501
        :type public_openssh: str
        :param login: The login of this SshKeyBastion.  # noqa: E501
        :type login: str
        :param gecos: The gecos of this SshKeyBastion.  # noqa: E501
        :type gecos: str
        :param status: The status of this SshKeyBastion.  # noqa: E501
        :type status: SshKeyStatus
        """
        self.swagger_types = {
            'public_openssh': str,
            'login': str,
            'gecos': str,
            'status': SshKeyStatus
        }

        self.attribute_map = {
            'public_openssh': 'public_openssh',
            'login': 'login',
            'gecos': 'gecos',
            'status': 'status'
        }
        self._public_openssh = public_openssh
        self._login = login
        self._gecos = gecos
        self._status = status

    @classmethod
    def from_dict(cls, dikt) -> 'SshKeyBastion':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The SshKeyBastion of this SshKeyBastion.  # noqa: E501
        :rtype: SshKeyBastion
        """
        return util.deserialize_model(dikt, cls)

    @property
    def public_openssh(self) -> str:
        """Gets the public_openssh of this SshKeyBastion.


        :return: The public_openssh of this SshKeyBastion.
        :rtype: str
        """
        return self._public_openssh

    @public_openssh.setter
    def public_openssh(self, public_openssh: str):
        """Sets the public_openssh of this SshKeyBastion.


        :param public_openssh: The public_openssh of this SshKeyBastion.
        :type public_openssh: str
        """

        self._public_openssh = public_openssh

    @property
    def login(self) -> str:
        """Gets the login of this SshKeyBastion.


        :return: The login of this SshKeyBastion.
        :rtype: str
        """
        return self._login

    @login.setter
    def login(self, login: str):
        """Sets the login of this SshKeyBastion.


        :param login: The login of this SshKeyBastion.
        :type login: str
        """

        self._login = login

    @property
    def gecos(self) -> str:
        """Gets the gecos of this SshKeyBastion.


        :return: The gecos of this SshKeyBastion.
        :rtype: str
        """
        return self._gecos

    @gecos.setter
    def gecos(self, gecos: str):
        """Sets the gecos of this SshKeyBastion.


        :param gecos: The gecos of this SshKeyBastion.
        :type gecos: str
        """

        self._gecos = gecos

    @property
    def status(self) -> SshKeyStatus:
        """Gets the status of this SshKeyBastion.


        :return: The status of this SshKeyBastion.
        :rtype: SshKeyStatus
        """
        return self._status

    @status.setter
    def status(self, status: SshKeyStatus):
        """Sets the status of this SshKeyBastion.


        :param status: The status of this SshKeyBastion.
        :type status: SshKeyStatus
        """

        self._status = status
