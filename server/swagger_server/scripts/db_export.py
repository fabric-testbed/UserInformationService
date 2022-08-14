"""
UIS to fabric-core-api migration
- People
- SshKeys

$ docker exec -u postgres uis-database psql -c '\dt;'
             List of relations
 Schema |      Name      | Type  |  Owner
--------+----------------+-------+----------
 public | author_ids     | table | postgres
 public | fabric_papers  | table | postgres
 public | fabric_people  | table | postgres
 public | fabric_sshkeys | table | postgres
 public | papers_authors | table | postgres
 public | version        | table | postgres
"""

import json
import logging

from swagger_server.database import Session
from swagger_server.database.models import DbSshKey, FabricPerson

logger = logging.getLogger(__file__)


# export people as JSON object
def dump_people_data():
    """
    People
    - id = Column(Integer, primary_key=True)
    - registered_on = Column(DateTime(timezone=True))
    - uuid = Column(String, unique=True)
    - oidc_claim_sub = Column(String)
    - name = Column(String)
    - email = Column(String)
    - eppn = Column(String)
    - bastion_login = Column(String)
    # store comanage ID here
    - co_person_id = Column(Integer)
    # preferences
    - settings = Column(JSONB)
    - permissions = Column(JSONB)
    - interests = Column(JSONB)
    # alternative IDs (scopus, orcid)
    - alt_ids = relationship('AuthorID', backref='owner')
    """
    with Session() as session:
        people = []
        fab_people = session.query(FabricPerson).order_by('id').all()
        for p in fab_people:
            data = {
                'id': p.id,
                'registered_on': str(p.registered_on),
                'uuid': p.uuid,
                'oidc_claim_sub': p.oidc_claim_sub,
                'name': p.name,
                'email': p.email,
                'eppn': p.eppn,
                'bastion_login': p.bastion_login,
                'co_person_id': p.co_person_id
            }
            people.append(data)
        output_dict = {'uis_people': people}
        output_json = json.dumps(output_dict, indent=2)
        print(json.dumps(output_dict, indent=2))
        with open("uis_people.json", "w") as outfile:
            outfile.write(output_json)


def dump_sshkey_data():
    """
    SshKeys
    - id = Column(Integer, primary_key=True)
    - key_uuid = Column(String)
    - comment = Column(String)
    # When received from user or returned to them
    # SSH public key has name, public_key and label in that order
    # e.g. 'ssh-dss <base 64 encoded public key> mykey'
    - description = Column(String)
    - ssh_key_type = Column(String)
    - fabric_key_type = Column(String)
    - fingerprint = Column(String)
    - created_on = Column(DateTime(timezone=True))
    # NOTE: not clear this index is enough to optimize searches for expired keys
    - expires_on = Column(DateTime(timezone=True), index=True)
    - active = Column(Boolean)
    - deactivation_reason = Column(String)
    - deactivated_on = Column(DateTime(timezone=True))
    - owner_uuid = Column(String, ForeignKey('fabric_people.uuid'))
    # if storing locally
    - public_key = Column(String)
    # if storing in COmanage
    - comanage_key_id = Column(String)
    """
    with Session() as session:
        sshkeys = []
        fab_sshkeys = session.query(DbSshKey).order_by('id').all()
        for p in fab_sshkeys:
            deactivated_on = str(p.deactivated_on) if p.deactivated_on else None
            data = {
                'id': p.id,
                'key_uuid': p.key_uuid,
                'comment': p.comment,
                'description': p.description,
                'ssh_key_type': p.ssh_key_type,
                'fabric_key_type': p.fabric_key_type,
                'fingerprint': p.fingerprint,
                'created_on': str(p.created_on),
                'expires_on': str(p.expires_on),
                'active': p.active,
                'deactivation_reason': p.deactivation_reason,
                'deactivated_on': deactivated_on,
                'owner_uuid': p.owner_uuid,
                'public_key': p.public_key,
                'comanage_key_id': p.comanage_key_id
            }
            sshkeys.append(data)
        output_dict = {'uis_sshkeys': sshkeys}
        output_json = json.dumps(output_dict, indent=2)
        print(json.dumps(output_dict, indent=2))
        with open("uis_sshkeys.json", "w") as outfile:
            outfile.write(output_json)


if __name__ == '__main__':
    logger.info("dump people table")
    dump_people_data()
    logger.info("dump sshkey table")
    dump_sshkey_data()
