import connexion
import six

from swagger_server.models.author_id import AuthorId  # noqa: E501
from swagger_server.models.author_id_type import AuthorIdType  # noqa: E501
from swagger_server import util
import swagger_server.response_code.publications_controller as pc


def authorids_idtype_uuid_get(idtype, uuid):  # noqa: E501
    """get users specific author ID

     # noqa: E501

    :param idtype: 
    :type idtype: dict | bytes
    :param uuid: 
    :type uuid: str

    :rtype: str
    """
    if connexion.request.is_json:
        idtype = connexion.request.from_dict(connexion.request.get_json())  # noqa: E501
    return pc.authorids_idtype_uuid_get(idtype, uuid)


def authorids_idtype_uuid_put(idtype, uuid, idval):  # noqa: E501
    """update user&#x27;s specific author ID

     # noqa: E501

    :param idtype: 
    :type idtype: dict | bytes
    :param uuid: 
    :type uuid: str
    :param idval: 
    :type idval: str

    :rtype: str
    """
    if connexion.request.is_json:
        idtype = connexion.request.from_dict(connexion.request.get_json())  # noqa: E501
    return pc.authorids_idtype_uuid_put(idtype, uuid, idval)


def authorids_uuid_get(uuid):  # noqa: E501
    """get user&#x27;s author IDs (Scopus, Orcid etc.)

     # noqa: E501

    :param uuid: 
    :type uuid: str

    :rtype: List[AuthorId]
    """
    return pc.authorids_uuid_get(uuid)
