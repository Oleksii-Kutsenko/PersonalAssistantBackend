"""Exceptions"""
from rest_framework.exceptions import APIException


class BadRequest(APIException):
    """
    BadRequest exception
    """
    status_code = 400
    default_code = 'bad_request'


class ServiceUnavailable(APIException):
    """
    The default exception for 503 HTTP code
    """
    status_code = 503
    default_detail = 'Service temporarily unavailable, try again later.'
