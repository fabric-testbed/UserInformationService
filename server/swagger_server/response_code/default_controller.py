from swagger_server.models.version import Version  # noqa: E501
from swagger_server.database.models import Version as DbVersion
from swagger_server.response_code.utils import log
from swagger_server.database import Session


def version_get():  # noqa: E501
    """version
    version # noqa: E501
    :rtype: Version
    """

    with Session() as session:
        log.info(f'Fetching version information')
        query_result = session.query(DbVersion).one()
        return Version(query_result.version, query_result.gitsha1)

