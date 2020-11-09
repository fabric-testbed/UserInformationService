# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class Preferences(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, settings: object=None, permissions: object=None, interests: object=None):  # noqa: E501
        """Preferences - a model defined in Swagger

        :param settings: The settings of this Preferences.  # noqa: E501
        :type settings: object
        :param permissions: The permissions of this Preferences.  # noqa: E501
        :type permissions: object
        :param interests: The interests of this Preferences.  # noqa: E501
        :type interests: object
        """
        self.swagger_types = {
            'settings': object,
            'permissions': object,
            'interests': object
        }

        self.attribute_map = {
            'settings': 'settings',
            'permissions': 'permissions',
            'interests': 'interests'
        }
        self._settings = settings
        self._permissions = permissions
        self._interests = interests

    @classmethod
    def from_dict(cls, dikt) -> 'Preferences':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Preferences of this Preferences.  # noqa: E501
        :rtype: Preferences
        """
        return util.deserialize_model(dikt, cls)

    @property
    def settings(self) -> object:
        """Gets the settings of this Preferences.


        :return: The settings of this Preferences.
        :rtype: object
        """
        return self._settings

    @settings.setter
    def settings(self, settings: object):
        """Sets the settings of this Preferences.


        :param settings: The settings of this Preferences.
        :type settings: object
        """

        self._settings = settings

    @property
    def permissions(self) -> object:
        """Gets the permissions of this Preferences.


        :return: The permissions of this Preferences.
        :rtype: object
        """
        return self._permissions

    @permissions.setter
    def permissions(self, permissions: object):
        """Sets the permissions of this Preferences.


        :param permissions: The permissions of this Preferences.
        :type permissions: object
        """

        self._permissions = permissions

    @property
    def interests(self) -> object:
        """Gets the interests of this Preferences.


        :return: The interests of this Preferences.
        :rtype: object
        """
        return self._interests

    @interests.setter
    def interests(self, interests: object):
        """Sets the interests of this Preferences.


        :param interests: The interests of this Preferences.
        :type interests: object
        """

        self._interests = interests
