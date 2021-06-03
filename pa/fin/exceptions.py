"""Exceptions"""
from rest_framework.exceptions import APIException


class BadRequest(APIException):
    """
    BadRequest exception
    """
    status_code = 400
    default_code = 'bad_request'
