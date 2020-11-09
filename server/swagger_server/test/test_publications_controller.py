# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.author_id import AuthorId  # noqa: E501
from swagger_server.models.author_id_type import AuthorIdType  # noqa: E501
from swagger_server.test import BaseTestCase


class TestPublicationsController(BaseTestCase):
    """PublicationsController integration test stubs"""

    def test_authorids_idtype_uuid_get(self):
        """Test case for authorids_idtype_uuid_get

        get users specific author ID
        """
        response = self.client.open(
            '//authorids/{idtype}/{uuid}'.format(idtype=AuthorIdType(), uuid='uuid_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_authorids_idtype_uuid_put(self):
        """Test case for authorids_idtype_uuid_put

        update user's specific author ID
        """
        query_string = [('idval', 'idval_example')]
        response = self.client.open(
            '//authorids/{idtype}/{uuid}'.format(idtype=AuthorIdType(), uuid='uuid_example'),
            method='PUT',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_authorids_uuid_get(self):
        """Test case for authorids_uuid_get

        get user's author IDs (Scopus, Orcid etc.)
        """
        response = self.client.open(
            '//authorids/{uuid}'.format(uuid='uuid_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
