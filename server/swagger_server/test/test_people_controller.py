# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.people_long import PeopleLong  # noqa: E501
from swagger_server.models.people_short import PeopleShort  # noqa: E501
from swagger_server.test import BaseTestCase


class TestPeopleController(BaseTestCase):
    """PeopleController integration test stubs"""

    def test_people_get(self):
        """Test case for people_get

        list of people (open to any valid user)
        """
        query_string = [('person_name', 'person_name_example')]
        response = self.client.open(
            '//people',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_people_uuid_get(self):
        """Test case for people_uuid_get

        person details by UUID (open only to self)
        """
        response = self.client.open(
            '//people/{uuid}'.format(uuid='uuid_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_people_whoami_get(self):
        """Test case for people_whoami_get

        Details about self from OIDC Claim sub provided in ID token; Creates new entry; (open only to self)
        """
        response = self.client.open(
            '//people/whoami',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_uuid_oidc_claim_sub_get(self):
        """Test case for uuid_oidc_claim_sub_get

        get person UUID based on their OIDC claim sub (open to any valid user)
        """
        query_string = [('oidc_claim_sub', 'oidc_claim_sub_example')]
        response = self.client.open(
            '//uuid/oidc_claim_sub',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
