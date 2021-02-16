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

from sqlalchemy import Column, Integer, String, ForeignKey, Table, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum, unique


Base = declarative_base()
metadata = Base.metadata


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
    registered_on = Column(TIMESTAMP)
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
    registered_on = Column(TIMESTAMP)
    uuid = Column(String)
    oidc_claim_sub = Column(String)
    name = Column(String)
    email = Column(String)
    eppn = Column(String)
    # store comanage ID here
    co_person_id = Column(String)
    # preferences
    settings = Column(JSONB)
    permissions = Column(JSONB)
    interests = Column(JSONB)
    # portal keys
    portal_keys = relationship('PortalKey', backref='owner')
    # user keys
    user_keys = relationship('UserKey', backref='owner')
    # alternative IDs (scopus, orcid)
    alt_ids = relationship('AuthorID', backref='owner')


class PortalKey(Base):
    """
    Portal-generated SSH keypairs
    """
    __tablename__ = 'portal_keys'

    id = Column(Integer, primary_key=True)
    keyid = Column(String)
    pubkey = Column(String)
    privkey = Column(String)
    registered_on = Column(TIMESTAMP)
    expires_on = Column(TIMESTAMP)
    owner_id = Column(Integer, ForeignKey('fabric_people.id'))


class UserKey(Base):
    """
    User public SSH keys
    """
    __tablename__ = 'user_keys'

    id = Column(Integer, primary_key=True)
    keyid = Column(String)
    pubkey = Column(String)
    registered_on = Column(TIMESTAMP)
    owner_id = Column(Integer, ForeignKey('fabric_people.id'))


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
    DUPLICATE_FOUND = 2


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
        return InsertOutcome.DUPLICATE_FOUND
    if len(query_result) > 1:
        return InsertOutcome.DUPLICATE_FOUND

    session.add(person)

    return InsertOutcome.OK


if __name__ == "__main__":
    print("[INFO] Creating tables")
    from swagger_server.database import engine
    metadata.create_all(engine)
