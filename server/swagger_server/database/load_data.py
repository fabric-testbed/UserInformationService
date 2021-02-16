#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#
# Author: Ilya Baldin (ibaldin@renci.org) Michael Stealey (stealey@renci.org)
from uuid import uuid4
import datetime
import re

import psycopg2
from ldap3 import Connection, Server, ALL

from swagger_server.database import Session, ldap_params
from swagger_server.database.models import FabricPerson, AuthorID, InsertOutcome, insert_unique_person


mock_people = [
    {
        'cn': 'System Administrator',
        'eduPersonPrincipalName': 'sysadmin@project-registry.org',
        'mail': 'sysadmin@project-registry.org',
        'uid': 'http://cilogon.org/serverA/users/000001',
        'settings': '{ "pref1": "val1" }'
    },
    {
        'cn': 'John Q. Public',
        'mail': 'public@project-registry.org',
        'uid': 'http://cilogon.org/serverA/users/000002',
        'orcid': '0000-0001-2345-6789',
        'scopus': '1234567890',
        'publons': 'G-1234-5678',
        'permissions': '{ "perm1": "val1" }'
    },
    {
        'cn': 'Eliza Fuller',
        'eduPersonPrincipalName': 'efuller@project-registry.org',
        'mail': 'efuller@not-project-registry.org',
        'uid': 'http://cilogon.org/serverT/users/12345678',
        'orcid': '1100-0001-2345-6789',
        'interests': '{ "int1": "val1" }',
        'settings': '{ "pref1": "val1" }'
    },
    {
        'cn': 'Kendra Theory',
        'eduPersonPrincipalName': 'ktheory@project-registry.org',
        'mail': 'ktheory@email.project-registry.org',
        'uid': 'http://cilogon.org/serverA/users/87654321',
        'orcid': '2200-0001-2345-6789',
        'publons': 'G-8765-4321'
    },
    {
        'cn': 'Yolanda Guerra',
        'eduPersonPrincipalName': 'yolanda@@project-registry.org',
        'mail': 'yolandaguerra@not-project-registry.org',
        'uid': 'http://cilogon.org/serverT/users/24681357',
        'orcid': '3300-0001-2345-6789',
        'scopus': '0987654321'
    }
]


def dict_from_query(query=None):
    session = Session()
    resultproxy = session.execute(query)
    session.close()

    d, a = {}, []
    for rowproxy in resultproxy:
        # rowproxy.items() returns an array like [(key0, value0), (key1, value1)]
        for column, value in rowproxy.items():
            # build up the dictionary
            d = {**d, **{column: value}}
        a.append(d)

    return a


def run_sql_commands(commands):

    session = Session()
    try:
        if isinstance(commands, tuple):
            for command in commands:
                session.execute(command)
        else:
            session.execute(commands)
        session.commit()
        print("[INFO] data loaded successfully!")
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if session is not None:
            session.close()


# Attributes to request from COmanage LDAP
ATTRIBUTES = [
    'cn',
    'eduPersonPrincipalName',
    'isMemberOf',
    'mail',
    'uid'
]


def get_people_list():
    """
    Get a list of people from COmanage
    """
    ldap_search_filter = '(objectclass=person)'
    server = Server(ldap_params['host'], use_ssl=True, get_info=ALL)
    conn = Connection(server, ldap_params['user'],
                      ldap_params['password'], auto_bind=True)
    objects_found = conn.search(
        ldap_params['search_base'],
        ldap_search_filter,
        attributes=ATTRIBUTES
    )
    people = []
    if objects_found:
        for entry in conn.entries:
            obj = {}
            for attr in ATTRIBUTES:
                if attr == 'isMemberOf':
                    print(str(attr) + ": " + str(entry[str(attr)]).strip("'"))
                    groups = []
                    for group in entry[attr]:
                        if re.search("(CO:COU:(?:\w+-{1})+\w+:members:active)", str(group)):
                            groups.append(str(group))
                    obj[str(attr)] = groups
                else:
                    print(str(attr) + ": " + str(entry[str(attr)]))
                    obj[str(attr)] = str(entry[str(attr)])
            people.append(obj)
    conn.unbind()
    return people


def load_version_data():
    commands = (
        """
        INSERT INTO version(id, version, gitsha1)
        VALUES (1, '1.0.0', 'd943bb9fd09e00a2fc672df344a087e8dd89ffb0')
        ON CONFLICT (id)
        DO UPDATE SET version = Excluded.version, gitsha1 = Excluded.gitsha1
        """
    )
    run_sql_commands(commands)


def load_people_data(flag):

    if flag == 'mock':
        people = mock_people
    elif flag == 'ldap':
        people = get_people_list()
    else:
        return

    session = Session()

    for person in people:
        people_uuid = uuid4()
        print(f"Adding {person.get('cn')} with GUID {people_uuid} to database")
        dbperson = FabricPerson()
        dbperson.uuid = people_uuid
        dbperson.registered_on = datetime.datetime.utcnow()
        dbperson.oidc_claim_sub = person.get('uid')
        dbperson.email = person.get('mail')
        dbperson.name = person.get('cn')
        dbperson.eppn = person.get('eduPersonPrincipalName')
        if person.get('settings', None) is not None:
            dbperson.settings = person.get('settings')
        if person.get('permissions', None) is not None:
            dbperson.permissions = person.get('permissions')
        if person.get('interests', None) is not None:
            dbperson.interests = person.get('interests')
        alt_ids = list()
        if person.get('publons', None) is not None:
            alt_ids.append(AuthorID(alt_id_type='publons',
                                    alt_id_value=person.get('publons')))
        if person.get('orcid', None) is not None:
            alt_ids.append(AuthorID(alt_id_type='orcid',
                                    alt_id_value=person.get('orcid')))
        if person.get('scopus', None) is not None:
            alt_ids.append(AuthorID(alt_id_type='scopus',
                                    alt_id_value=person.get('orcid')))
        dbperson.alt_ids = alt_ids
        ret = insert_unique_person(dbperson, session)
        if ret != InsertOutcome.OK:
            print(f"Unable to add entry for {dbperson.oidc_claim_sub} due to {ret}. "
                  f"For a pre-existing entry, some fields (name, email, eppn) may have been updated")
    session.commit()


if __name__ == '__main__':
    load_version_data()
    load_people_data('mock')