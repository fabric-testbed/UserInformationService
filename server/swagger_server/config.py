from configparser import ConfigParser
import os


def config_from_file(filename='ini/pr_database.ini', section='postgres'):
    """
    Configure from an INI file
    :param filename: path to ini file
    :param section: name of the section in the INI file to turn into a dictionary
    :return: a dictionary of config values.
    """

    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgres
    params = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            params[item[0]] = item[1]

    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return params


def config_from_env(prefix):
    """
    Configure from the environment based on expected prefix of environment
    variables. Returned dictionary has the prefix + '_' stripped off and the
    second part of variable name turned to lower case (for consistency with INI
    parsing).
    :param prefix: prefix for env variable (expected to have PREFIX_ form)
    """
    params = dict()
    mypref = prefix + '_'
    for var, val in os.environ.items():
        if var.startswith(mypref):
            params[var[len(mypref):].lower()] = val

    return params
