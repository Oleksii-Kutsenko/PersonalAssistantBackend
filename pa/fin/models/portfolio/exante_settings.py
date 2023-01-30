"""
ExanteSettings model and related models
"""
import datetime
import time

import jwt
import requests
from django.db import models


class ExanteSettings(models.Model):
    """
    Model that represents parameters for the access the Exante Api
    """

    exante_account_id = models.CharField(max_length=50)
    iss = models.CharField(max_length=50)
    sub = models.CharField(max_length=50)
    portfolio = models.OneToOneField("Portfolio", on_delete=models.CASCADE)

    def get_account_summary(self, token):
        """
        Returns account summary in json format
        """
        currency = "USD"
        version = "3.0"
        account_summary_url = f"https://api-live.exante.eu/md/{version}/summary/{self.exante_account_id}/{currency}/"
        response = requests.get(
            account_summary_url, headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()

    def get_jwt(self, secret_key):
        """
        Generate jwt for EXANTE API
        """
        return jwt.encode(
            {
                "iss": self.iss,
                "sub": self.sub,
                "iat": int(time.mktime(datetime.datetime.utcnow().timetuple())),
                "exp": int(
                    time.mktime(
                        (
                            datetime.datetime.utcnow() + datetime.timedelta(days=1)
                        ).timetuple()
                    )
                ),
                "aud": [
                    "symbols",
                    "ohlc",
                    "feed",
                    "change",
                    "crossrates",
                    "orders",
                    "summary",
                    "accounts",
                    "transactions",
                ],
            },
            secret_key,
        )
