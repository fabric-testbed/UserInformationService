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
from typing import List, Any
from uuid import uuid4
import datetime
import re

import psycopg2
import requests
from requests.auth import HTTPBasicAuth
from ldap3 import Connection, Server, ALL

from swagger_server.database import Session, ldap_params, COID, COAPI_USER, COAPI_KEY, CO_REGISTRY_URL
from swagger_server.database.models import FabricPerson, AuthorID, InsertOutcome, insert_unique_person

from . import metadata, engine

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


def comanage_load_all_people(do_database = True):
    """
    Load people from COmanage. Setting do_database to False
    allows to test retrieving data from COmanage without writing to db
    """
    #
    # Get a list of active OIDC subs
    #
    if do_database:
        session = Session()
    else:
        session = None

    params = {'coid': COID}
    response = requests.get(url=CO_REGISTRY_URL + 'co_people.json',
                            params=params,
                            auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
    if response.status_code == requests.codes.ok:
        people_data = response.json()
        co_people = people_data['CoPeople'] if people_data.get('CoPeople', None) is not None else list()
        # produce a list of tuples <oidc sub, coperson id> for each person
        person_ids = list(map(lambda x: (x['ActorIdentifier'], x['Id']),
                             filter(lambda x: x['Status'] == 'Active',
                                    co_people)))
    else:
        print(f'Unable to get people from COmanage due to {response=}')
        return
    for ids in person_ids:
        # ids[0] oidc claim sub (url)
        # ids[1] copersonid (numeric)
        # get the person's particulars and enter them in DB issuing a fresh GUID

        # identifiers
        response = requests.get(
            url=CO_REGISTRY_URL + 'identifiers.json',
            params={'copersonid': ids[1]},
            auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
        oidc_claim_sub = None
        eppn = None
        if response.status_code == requests.codes.ok:
            data = response.json()
            for identifier in data['Identifiers']:
                if identifier['Type'] == 'oidcsub':
                    oidc_claim_sub = identifier['Identifier']
                    if oidc_claim_sub != ids[0]:
                        print(f"OIDC claim sub received from identifiers {oidc_claim_sub=} does not match one "
                              f"received from people {ids[0]=}")
                    break
                if identifier['Type'] == 'eppn':
                    eppn = identifier['Identifier']
        else:
            print(f"Unable to get identifiers from COmanage for {ids[0]}, {ids[1]} due to {response=}")
            continue
        if oidc_claim_sub is None:
            oidc_claim_sub = ids[0]

        # names
        response = requests.get(
            url=CO_REGISTRY_URL + 'names.json',
            params={'copersonid': ids[1], 'coid': COID},
            auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
        if response.status_code == requests.codes.ok:
            response_obj = response.json()
            names_list = response_obj.get('Names', None)
            if names_list is None or len(names_list) == 0:
                continue
            # use the first name entry
            names = names_list[0]
            name = " ".join([names.get('Given', ""),
                             names.get('Middle', ""),
                             names.get('Family', ""),
                             names.get('Suffix', "")])
            if len(name) == 3:
                name = 'No Name Given'

            # strip extra spaces
            name = re.sub(' +', ' ', name)
        else:
            print(f"Unable to get name and/or email from COmanage for {ids[0]}, {ids[1]} due to {response=}")
            continue

        # email
        email = None
        response = requests.get(
            url=CO_REGISTRY_URL + 'email_addresses.json',
            params={'copersonid': ids[1], 'coid': COID},
            auth=HTTPBasicAuth(COAPI_USER, COAPI_KEY))
        if response.status_code == requests.codes.ok:
            response_obj = response.json()
            try:
                email = response_obj['EmailAddresses'][0]['Mail']
            except KeyError:
                pass

        print(f"Adding active person {oidc_claim_sub=}, {name=}, {eppn=}, {email=}")
        people_uuid = uuid4()
        print(f"Adding {name=} with GUID {people_uuid} to database")

        if do_database:
            dbperson = FabricPerson()
            dbperson.uuid = people_uuid
            dbperson.registered_on = datetime.datetime.utcnow()
            dbperson.oidc_claim_sub = oidc_claim_sub
            dbperson.email = email
            dbperson.name = name
            dbperson.eppn = eppn

            ret = insert_unique_person(dbperson, session)
            if ret != InsertOutcome.OK and ret != InsertOutcome.DUPLICATE_UPDATED:
                print(f"Unable to add or update entry for {dbperson.oidc_claim_sub} due to {ret}. ")
            session.commit()


def drop_recreate():
    """
    Drop and recreate all tables
    """
    print("CAUTION: Dropping and recreating all tables")
    metadata.drop_all(engine)
    metadata.create_all(engine)


def load_people_data(flag):

    if flag == 'mock':
        people = mock_people
    elif flag == 'ldap':
        people = get_people_list()
    elif flag == 'rest':
        # uses newer format and doesn't need the code below
        drop_recreate()
        comanage_load_all_people(False)
        return
    else:
        # leave everything untouched
        return

    # drop and recreate all tables
    drop_recreate()

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
        if ret != InsertOutcome.OK and ret != InsertOutcome.DUPLICATE_UPDATED:
            print(f"Unable to add entry for {dbperson.oidc_claim_sub} due to {ret}. ")
    session.commit()


if __name__ == '__main__':
    load_version_data()
    load_people_data('mock')