import connexion
import six

from swagger_server.models.people_long import PeopleLong  # noqa: E501
from swagger_server.models.people_short import PeopleShort  # noqa: E501
from swagger_server import util
import swagger_server.response_code.people_controller as pc


def people_get(person_name=None, x_page_no=None):  # noqa: E501
    """list of people

    List of people # noqa: E501

    :param person_name: Search People by Name (ILIKE)
    :type person_name: str
    :param x_page_no: Page number of results (25 per page)
    :type x_page_no: str

    :rtype: List[PeopleShort]
    """
    return pc.people_get(person_name, x_page_no)


def people_oidc_claim_sub_get(oidc_claim_sub):  # noqa: E501
    """person details by OIDC Claim sub

    Person details by OIDC Claim sub # noqa: E501

    :param oidc_claim_sub: Search People by OIDC Claim sub (exact match only)
    :type oidc_claim_sub: str

    :rtype: List[PeopleLong]
    """
    return pc.people_oidc_claim_sub_get(oidc_claim_sub)


def people_uuid_get(uuid):  # noqa: E501
    """person details by UUID

    Person details by UUID # noqa: E501

    :param uuid: People identifier as UUID
    :type uuid: str

    :rtype: PeopleLong
    """
    return pc.people_uuid_get(uuid)
