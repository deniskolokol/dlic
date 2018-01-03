class DmException(Exception):
    pass


class InternalException(DmException):
    pass


class InvalidDataFile(DmException):
    pass


class InvalidCSV(InvalidDataFile):
    pass


class InvalidTimeseries(InvalidDataFile):
    pass


class ApiResponseNotOk(DmException):
    pass
