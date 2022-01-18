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
# Author: Ilya Baldin (ibaldin@renci.org), Michael Stealey (stealey@renci.org)

from sqlalchemy import Column, Integer, String, ForeignKey, Table, Boolean, Index, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum, unique

from . import Base, metadata


# secondary table for papers-to-authors many-to-many
PapersAuthors = Table(
    'papers_authors',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('papers_id', Integer, ForeignKey('fabric_papers.id')),
    Column('authors_id', Integer, ForeignKey('fabric_people.id'))
)


class FabricPaper(Base):
    """
    Attributable publications written using FABRIC
    """
    __tablename__ = 'fabric_papers'

    id = Column(Integer, primary_key=True)
    registered_on = Column(DateTime(timezone=True))
    doi = Column(String)
    title = Column(String)
    authors_as_text = Column(String)
    venue = Column(String)
    publisher = Column(String)
    # prolly should add constraints /ib
    # many pubs lack exact date, so better to specify columns separately instead of DATETIME
    year = Column(Integer)
    month = Column(Integer)
    day = Column(Integer)
    # many to many papers to people
    paper_authors = relationship('FabricPerson', secondary=PapersAuthors, backref='FabricPaper')


class FabricPerson(Base):
    """
    FABRIC People information
    """
    __tablename__ = 'fabric_people'

    id = Column(Integer, primary_key=True)
    registered_on = Column(DateTime(timezone=True))
    uuid = Column(String, unique=True)
    oidc_claim_sub = Column(String)
    name = Column(String)
    email = Column(String)
    eppn = Column(String)
    bastion_login = Column(String)
    # store comanage ID here
    co_person_id = Column(Integer)
    # preferences
    settings = Column(JSONB)
    permissions = Column(JSONB)
    interests = Column(JSONB)
    # alternative IDs (scopus, orcid)
    alt_ids = relationship('AuthorID', backref='owner')


class DbSshKey(Base):
    """
    SSH key storage. Keys can be sliver or bastion.
    They can be forcibly deactivated or they can expire.
    """
    __tablename__ = 'fabric_sshkeys'

    id = Column(Integer, primary_key=True)
    key_uuid = Column(String)
    comment = Column(String)
    # When received from user or returned to them
    # SSH public key has name, public_key and label in that order
    # e.g. 'ssh-dss <base 64 encoded public key> mykey'
    description = Column(String)
    ssh_key_type = Column(String)
    fabric_key_type = Column(String)
    fingerprint = Column(String)
    created_on = Column(DateTime(timezone=True))
    # NOTE: not clear this index is enough to optimize searches for expired keys
    expires_on = Column(DateTime(timezone=True), index=True)
    active = Column(Boolean)
    deactivation_reason = Column(String)
    deactivated_on = Column(DateTime(timezone=True))
    owner_uuid = Column(String, ForeignKey('fabric_people.uuid'))
    # if storing locally
    public_key = Column(String)
    # if storing in COmanage
    comanage_key_id = Column(String)

    Index('idx_owner_keyid_keytype', 'type', 'owner_uuid', 'key_uuid')
    Index('idx_owner_fingerprint', 'owner_uuid', 'fingerprint')


class AuthorID(Base):
    __tablename__ = 'author_ids'

    id = Column(Integer, primary_key=True)
    # e.g. 'scopus' or 'orcid'
    alt_id_type = Column(String)
    alt_id_value = Column(String)
    owner_id = Column(Integer, ForeignKey('fabric_people.id'))


class Version(Base):
    """
    FABRIC API Version information
    """
    __tablename__ = 'version'

    id = Column(Integer, primary_key=True)
    version = Column(String)
    gitsha1 = Column(String)


@unique
class PreferenceType(Enum):
    settings = 1
    permissions = 2
    interests = 3


@unique
class InsertOutcome(Enum):
    OK = 0
    UNIQUE_FIELD_MISSING = 1
    DUPLICATE_UPDATED = 2
    MULTIPLE_DUPLICATES_FOUND = 3


def insert_unique_person(person: FabricPerson, session) -> InsertOutcome:
    """
    Insert a unique person without creating a duplicate, based on
    OIDC claim sub. Does session.add(), but DOES NOT do session.commit()
    :return val: 0 - OK, 1 - OIDC claim sub missing, 2 - duplicate
    entry
    """
    if person.oidc_claim_sub is None:
        return InsertOutcome.UNIQUE_FIELD_MISSING

    query = session.query(FabricPerson).\
        filter(FabricPerson.oidc_claim_sub == person.oidc_claim_sub)

    query_result = query.all()

    if len(query_result) == 1:
        # entry exists
        # compare name, email and eppn and update
        update_attributes = ['name', 'email', 'eppn']
        dbperson = query_result[0]
        for attr in update_attributes:
            if getattr(dbperson, attr) != getattr(person, attr):
                setattr(dbperson, attr, getattr(person, attr))
        # commit should be called later
        return InsertOutcome.DUPLICATE_UPDATED
    if len(query_result) > 1:
        return InsertOutcome.MULTIPLE_DUPLICATES_FOUND

    session.add(person)

    return InsertOutcome.OK


if __name__ == "__main__":
    print("[INFO] Creating tables")
    from swagger_server.database import engine
    metadata.create_all(engine)
