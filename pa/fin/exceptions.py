"""Exceptions"""
from rest_framework.exceptions import APIException


class BadRequest(APIException):
    """
    BadRequest exception
    """
    status_code = 400
    default_code = 'bad_request'


class WebSocketException(Exception):

    def __init__(self, base_exception=None, detail=None):
        if base_exception is None:
            base_exception = Exception(detail)

        self.exception_type = base_exception.__class__.__name__
        self.exception_detail = base_exception

        super(WebSocketException, self).__init__()

    def to_json(self):
        """
        Returns json representation of the exception
        """
        return {'class': self.__class__.__name__,
                'detail': f'{self.exception_type}: {str(self.exception_detail)}'}


class FormatError(WebSocketException):
    pass


class InvalidData(WebSocketException):
    pass


class InvalidMessageType(WebSocketException):
    pass
