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
import requests
from ldap3 import Connection, Server, ALL

from fss_utils.sshkey import FABRICSSHKey

from swagger_server.database import Session, ldap_params, co_api
from swagger_server.database.models import FabricPerson, AuthorID, InsertOutcome, insert_unique_person
from . import __VERSION__, log

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

def run_sql_commands(commands):

    with Session() as session:
        try:
            if isinstance(commands, tuple):
                for command in commands:
                    session.execute(command)
            else:
                session.execute(commands)
            session.commit()
            log.info("Data loaded successfully!")
        except (Exception, psycopg2.DatabaseError) as error:
            log.error(error)


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
                    log.debug(str(attr) + ": " + str(entry[str(attr)]).strip("'"))
                    groups = []
                    for group in entry[attr]:
                        if re.search("(CO:COU:(?:\w+-{1})+\w+:members:active)", str(group)):
                            groups.append(str(group))
                    obj[str(attr)] = groups
                else:
                    log.debug(str(attr) + ": " + str(entry[str(attr)]))
                    obj[str(attr)] = str(entry[str(attr)])
            people.append(obj)
    conn.unbind()
    return people


def load_version_data():
    commands = (
        f"""
        INSERT INTO version(id, version, gitsha1)
        VALUES (1, '{__VERSION__}', 'd943bb9fd09e00a2fc672df344a087e8dd89ffb0')
        ON CONFLICT (id)
        DO UPDATE SET version = Excluded.version, gitsha1 = Excluded.gitsha1
        """
    )
    run_sql_commands(commands)


def comanage_load_all_people(do_database=True):
    """
    Load people from COmanage. Setting do_database to False
    allows to test retrieving data from COmanage without writing to db
    """
    #
    # Get a list of active OIDC subs
    #

    try:
        response_obj = co_api.copeople_view_per_co()
        if not response_obj:
            log.info('copeople_view_per_co returned no data, exiting')
            return
    except requests.HTTPError as e:
        log.error(f"COmanage request exception {e} encountered in co_people_view_per_co, returning")
        return

    co_people = response_obj['CoPeople'] if response_obj.get('CoPeople', None) is not None else list()
    # produce a list of tuples <oidc sub, coperson id> for each person
    person_ids = list(map(lambda x: (x['ActorIdentifier'], x['Id']),
                          filter(lambda x: x['Status'] == 'Active',
                                 co_people)))

    if do_database:
        session = Session()
    else:
        session = None

    for ids in person_ids:
        # ids[0] oidc claim sub (url)
        # ids[1] copersonid (numeric)
        # get the person's particulars and enter them in DB issuing a fresh GUID

        # identifiers
        try:
            data = co_api.identifiers_view_per_entity(None, ids[1])
            if not data:
                continue
        except requests.HTTPError as e:
            log.error(f"COmanage request exception {e} encountered in identifiers.json")
            continue

        oidc_claim_sub = None
        eppn = None

        for identifier in data['Identifiers']:
            if identifier['Type'] == 'oidcsub':
                oidc_claim_sub = identifier['Identifier']
                if oidc_claim_sub != ids[0]:
                    log.warn(f"OIDC claim sub received from identifiers {oidc_claim_sub=} does not match one "
                             f"received from people {ids[0]=}")
                break
            if identifier['Type'] == 'eppn':
                eppn = identifier['Identifier']

        if oidc_claim_sub is None:
            oidc_claim_sub = ids[0]

        # names
        try:
            response_obj = co_api.names_view_per_person(None, ids[1])
            if not response_obj:
                return 200, None
        except requests.HTTPError as e:
            log.error(f"COmanage request exception {e} encountered in names.json")
            continue

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

        # email
        email = None
        try:
            response_obj = co_api.email_addresses_view_per_person(None, ids[1])
        except requests.HTTPError as e:
            log.error(f'COmanage request exception {e} encountered in emails.json')
            continue

        try:
            email = response_obj['EmailAddresses'][0]['Mail']
        except KeyError:
            pass

        bastion_login = FABRICSSHKey.bastion_login(oidc_claim_sub, email)

        people_uuid = uuid4()

        if do_database:
            log.info(f"Adding active person {oidc_claim_sub=}, {name=}, {eppn=}, "
                     f"{email=} with GUID {people_uuid} and bastion login {bastion_login} to database")
            dbperson = FabricPerson()
            dbperson.uuid = people_uuid
            dbperson.registered_on = datetime.datetime.utcnow()
            dbperson.oidc_claim_sub = oidc_claim_sub
            dbperson.email = email
            dbperson.name = name
            dbperson.eppn = eppn
            dbperson.bastion_login = bastion_login

            ret = insert_unique_person(dbperson, session)
            if ret == InsertOutcome.DUPLICATE_UPDATED:
                log.info(f"Updated a pre-existing entry for {dbperson.oidc_claim_sub} ({dbperson.name=})")
            if ret != InsertOutcome.OK and ret != InsertOutcome.DUPLICATE_UPDATED:
                log.error(f"Unable to add or update entry for {dbperson.oidc_claim_sub} due to {ret}. ")
            session.commit()
        else:
            log.info(f"Skipping adding person {oidc_claim_sub=}, {name=}, {eppn=}, "
                     f"{email=} with GUID {people_uuid} and bastion login {bastion_login} to database - "
                     f"do_database flag is False")
    if session:
        session.close()


def load_people_data(mode):
    """
    mode can be 'mock', 'ldap' or 'rest'
    """

    if mode == 'mock':
        log.info("Using mock data")
        people = mock_people
    elif mode == 'ldap':
        log.info("Using LDAP to load people data")
        people = get_people_list()
    elif mode == 'rest':
        log.info("Using COmanage REST to load people data")
        # uses newer format and doesn't need the code below
        comanage_load_all_people()
        return
    else:
        # leave everything untouched
        return

    with Session() as session:
        for person in people:
            people_uuid = uuid4()
            log.info(f"Adding {person.get('cn')} with GUID {people_uuid} to database")
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
                log.error(f"Unable to add entry for {dbperson.oidc_claim_sub} due to {ret}. ")
        session.commit()


if __name__ == '__main__':
    load_version_data()
    load_people_data('mock')