import connexion
import six

from swagger_server.models.preferences import Preferences  # noqa: E501
import swagger_server.response_code.preferences_controller as pc


def preferences_preftype_uuid_get(preftype, uuid):  # noqa: E501
    """get user preferences of specific type (settings, permissions or interests; open only to self)

    User preferences (returns sane defaults if user valid, but preferences not available) # noqa: E501

    :param preftype: 
    :type preftype: dict | bytes
    :param uuid: 
    :type uuid: str

    :rtype: object
    """
    if connexion.request.is_json:
        preftype = connexion.request.from_dict(connexion.request.get_json())  # noqa: E501
    return pc.preferences_preftype_uuid_get(preftype, uuid)


def preferences_preftype_uuid_put(uuid, preftype, preferences):  # noqa: E501
    """update user preferences by type (open only to self)

    Update specific type of user preferences # noqa: E501

    :param uuid: 
    :type uuid: str
    :param preftype: 
    :type preftype: dict | bytes
    :param preferences: 
    :type preferences: Dict[str, ]

    :rtype: str
    """
    if connexion.request.is_json:
        preftype = connexion.request.from_dict(connexion.request.get_json())  # noqa: E501
    return pc.preferences_preftype_uuid_put(uuid, preftype, preferences)


def preferences_uuid_get(uuid):  # noqa: E501
    """get all user preferences as an object (open only to self)

    Get all preferences for a user # noqa: E501

    :param uuid: 
    :type uuid: str

    :rtype: Preferences
    """
    return pc.preferences_uuid_get(uuid)
