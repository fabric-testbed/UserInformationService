# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.preference_type import PreferenceType  # noqa: E501
from swagger_server.models.preferences import Preferences  # noqa: E501
from swagger_server.test import BaseTestCase


class TestPreferencesController(BaseTestCase):
    """PreferencesController integration test stubs"""

    def test_preferences_preftype_uuid_get(self):
        """Test case for preferences_preftype_uuid_get

        get user preferences of specific type (settings, permissions or interests; open only to self)
        """
        response = self.client.open(
            '//preferences/{preftype}/{uuid}'.format(preftype=PreferenceType(), uuid='uuid_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_preferences_preftype_uuid_put(self):
        """Test case for preferences_preftype_uuid_put

        update user preferences by type (open only to self)
        """
        query_string = [('preferences', None)]
        response = self.client.open(
            '//preferences/{preftype}/{uuid}'.format(uuid='uuid_example', preftype=PreferenceType()),
            method='PUT',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_preferences_uuid_get(self):
        """Test case for preferences_uuid_get

        get all user preferences as an object (open only to self)
        """
        response = self.client.open(
            '//preferences/{uuid}'.format(uuid='uuid_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
