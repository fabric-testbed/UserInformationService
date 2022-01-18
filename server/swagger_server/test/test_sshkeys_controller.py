# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.ssh_key_bastion import SshKeyBastion  # noqa: E501
from swagger_server.models.ssh_key_long import SshKeyLong  # noqa: E501
from swagger_server.models.ssh_key_pair import SshKeyPair  # noqa: E501
from swagger_server.models.ssh_key_type import SshKeyType  # noqa: E501
from swagger_server.test import BaseTestCase


class TestSshkeysController(BaseTestCase):
    """SshkeysController integration test stubs"""

    def test_bastionkeys_get(self):
        """Test case for bastionkeys_get

        Get a list of bastion keys that were created, deactivated or expired since specified date in UTC (open to Bastion hosts)
        """
        query_string = [('secret', 'secret_example'),
                        ('since_date', 'since_date_example')]
        response = self.client.open(
            '//bastionkeys',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sshkey_keyid_delete(self):
        """Test case for sshkey_keyid_delete

        Delete a specified key based on key UUID (open only to self)
        """
        response = self.client.open(
            '//sshkey/{keyid}'.format(keyid='keyid_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sshkey_keyid_get(self):
        """Test case for sshkey_keyid_get

        get metadata, including expiration date for this key based on key UUID (open only to self)
        """
        response = self.client.open(
            '//sshkey/{keyid}'.format(keyid='keyid_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sshkey_keytype_post(self):
        """Test case for sshkey_keytype_post

        Add a user-provided ssh public key of specified type. (open only to self)
        """
        query_string = [('public_openssh', 'public_openssh_example'),
                        ('description', 'description_example')]
        response = self.client.open(
            '//sshkey/{keytype}'.format(keytype=SshKeyType()),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sshkey_keytype_put(self):
        """Test case for sshkey_keytype_put

        Generate a new SSH key of specified type. Return both public and private portions. (open only to self)
        """
        query_string = [('comment', 'comment_example'),
                        ('description', 'description_example')]
        response = self.client.open(
            '//sshkey/{keytype}'.format(keytype=SshKeyType()),
            method='PUT',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sshkey_uuid_keyid_get(self):
        """Test case for sshkey_uuid_keyid_get

        Get a specific key of a given user (open to any valid user)
        """
        response = self.client.open(
            '//sshkey/{uuid}/{keyid}'.format(uuid='uuid_example', keyid='keyid_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sshkeys_get(self):
        """Test case for sshkeys_get

        Get a list of all active/non-expired keys of this user (open to self)
        """
        response = self.client.open(
            '//sshkeys',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
