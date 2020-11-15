import connexion
import six

from swagger_server.models.version import Version  # noqa: E501
from swagger_server import util
import swagger_server.response_code.default_controller as dc


def version_get():  # noqa: E501
    """version (open)

    Version # noqa: E501


    :rtype: Version
    """
    return dc.version_get()
