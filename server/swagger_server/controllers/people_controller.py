import connexion
import six

from swagger_server.models.people_long import PeopleLong  # noqa: E501
import swagger_server.response_code.people_controller as pc


def people_get(person_name=None):  # noqa: E501
    """list of people (open to any valid user)

    List of people # noqa: E501

    :param person_name: Search People by Name (ILIKE)
    :type person_name: str

    :rtype: List[PeopleShort]
    """
    return pc.people_get(person_name)


def people_uuid_get(uuid):  # noqa: E501
    """person details by UUID (open only to self)

    Person details by UUID # noqa: E501

    :param uuid: People identifier as UUID
    :type uuid: str

    :rtype: PeopleLong
    """
    return pc.people_uuid_get(uuid)


def people_whoami_get():  # noqa: E501
    """Details about self from OIDC Claim sub provided in ID token (open only to self)

    Details about self based on key OIDC Claim sub contained in ID token # noqa: E501


    :rtype: List[PeopleLong]
    """
    return pc.people_whoami_get()


def uuid_oidc_claim_sub_get(oidc_claim_sub):  # noqa: E501
    """get person UUID based on their OIDC claim sub (open to any valid user)

    person UUID based on their OIDC claim sub # noqa: E501

    :param oidc_claim_sub: 
    :type oidc_claim_sub: str

    :rtype: str
    """
    return pc.uuid_oidc_claim_sub_get(oidc_claim_sub)
