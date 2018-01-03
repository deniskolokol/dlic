from rest_framework.exceptions import APIException


class APINotFound(APIException):
    status_code = 404
    default_detail = {'status': 'fail', 'problem': 'Not found'}


class APIPermissionDenied(APIException):
    status_code = 403
    default_detail = {'status': 'fail', 'problem': 'Permission denied'}


class APIUserDoesNotPaid(APIException):
    status_code = 403
    default_detail = {
        'status': 'fail',
        'problem': 'You do not have paid time. Purchase time to continue'
    }


class APIBadRequest(APIException):
    status_code = 400
    default_detail = {'status': 'fail', 'problem': 'Bad request.'}


class APIStandardError(APIException):
    status_code = 503
    default_detail = {'status': 'fail', 'problem': 'API Error.'}
