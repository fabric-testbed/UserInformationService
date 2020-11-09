from uuid import uuid4

import psycopg2

from swagger_server.database import Session
from swagger_server.database.models import FabricPerson, AuthorID


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


def load_version_data():
    commands = (
        """
        INSERT INTO version(id, version, gitsha1)
        VALUES (1, '1.0.0', 'd943bb9fd09e00a2fc672df344a087e8dd89ffb0')
        ON CONFLICT (id)
        DO UPDATE SET version = Excluded.version, gitsha1 = Excluded.gitsha1
        """
    )
    print("[INFO] attempt to load version data")
    run_sql_commands(commands)


def load_people_data():
    people = mock_people

    session = Session()

    for person in people:
        people_uuid = uuid4()
        print(f"Adding {person.get('cn')} with GUID {people_uuid} to database")
        dbperson = FabricPerson()
        dbperson.uuid = people_uuid
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
        session.add(dbperson)
    session.commit()


if __name__ == '__main__':
    load_version_data()
    load_people_data()