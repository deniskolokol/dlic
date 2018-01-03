from .conf import settings
from logbook import Logger


def get_logger(name='ersatz', level=None):
    level = settings.LOGLEVEL if level is None else level
    log = Logger(name)
    log.level_name = settings.LOGLEVEL
    return log
