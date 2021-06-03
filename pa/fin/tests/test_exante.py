"""
Exante API tests
"""
import os

from jsonschema import validate, ValidationError

from fin.external_api.exante import get_jwt, get_account_summary
from fin.tests.base import BaseTestCase


class ExanteTests(BaseTestCase):
    """
    Exante API test cases
    """

    def test_get_account_summary(self):
        """
        Test Exante API response structure
        """
        token = get_jwt()
        account_summary = get_account_summary(os.environ.get('ACCOUNT_ID'), token)

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.com/product.schema.json",
            "title": "Account Summary",
            "description": "Response from EXANTE API",
            "type": "object",
            "properties": {
                "currencies": {
                    "description": "Money accounts",
                    "type": "array",
                    "items": {
                        "$ref": "#/$defs/currency"
                    },
                    "minItems": 1,
                    "uniqueItems": True
                },
                "timestamp": {
                    "type": "integer"
                },
                "freeMoney": {
                    "type": "string"
                },
                "netAssetValue": {
                    "type": "string"
                },
                "accountId": {
                    "type": "string"
                },
                "moneyUsedForMargin": {
                    "type": "string"
                },
                "marginUtilization": {
                    "type": "string"
                },
                "positions": {
                    "type": "array",
                    "items": {
                        "$refs": "#/$defs/position"
                    },
                    "minItems": 0,
                    "uniqueItems": True
                },
                "sessionDate": {
                    "type": "null"
                },
                "currency": {
                    "type": "string"
                }
            },
            "required": [
                "currencies",
                "timestamp",
                "freeMoney",
                "netAssetValue",
                "accountId",
                "moneyUsedForMargin",
                "marginUtilization",
                "positions",
                "sessionDate",
                "currency"
            ],
            "$defs": {
                "currency": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string"
                        },
                        "convertedValue": {
                            "type": "string"
                        },
                        "value": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "code",
                        "convertedValue",
                        "value"
                    ]
                },
                "position": {
                    "type": "object",
                    "properties": {
                        "convertedPnl": {
                            "type": "string"
                        },
                        "quantity": {
                            "type": "string"
                        },
                        "pnl": {
                            "type": "string"
                        },
                        "symbolId": {
                            "type": "string"
                        },
                        "convertedValue": {
                            "type": "string"
                        },
                        "price": {
                            "type": "string"
                        },
                        "symbolType": {
                            "type": "string"
                        },
                        "currency": {
                            "type": "string"
                        },
                        "averagePrice": {
                            "type": "string"
                        },
                        "value": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "convertedPnl",
                        "quantity",
                        "pnl",
                        "symbolId",
                        "convertedValue",
                        "price",
                        "symbolType",
                        "currency",
                        "averagePrice",
                        "value"
                    ]
                }
            }
        }
        try:
            validate(account_summary, schema)
        except ValidationError as validation_error:
            self.fail(validation_error)
