"""
WebSocket consumers and its utils
"""
from enum import Enum
import json

from decimal import InvalidOperation, Decimal
from channels.generic.websocket import JsonWebsocketConsumer

from django.core.exceptions import ObjectDoesNotExist

from fin.exceptions import FormatError, InvalidData, WebSocketException, InvalidMessageType
from fin.models import Index


class WebSocketMessageType(Enum):
    message = 0
    error = 1


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=E0202
        if isinstance(o, Decimal):
            return float(o)
        return super(ExtendedJSONEncoder, self).default(o)


class WebSocketMessage:

    def __init__(self, message_type, message):
        self.message_type = message_type
        self.message = message

    def __str__(self):
        return json.dumps({
            'type': self.message_type,
            'message': self.message
        }, cls=ExtendedJSONEncoder)


class ErrorWebSocketMessage(WebSocketMessage):

    def __init__(self, message):
        if isinstance(message, WebSocketException):
            super(ErrorWebSocketMessage, self).__init__(WebSocketMessageType.error.value, message)
        else:
            raise Exception('Invalid type of message')

    def __str__(self):
        return json.dumps({
            'type': self.message_type,
            'message': self.message.to_json()
        })


class AdjustedIndexConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, code):
        pass

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data:
            self.receive_json(self.decode_json(text_data), **kwargs)
        else:
            msg = ErrorWebSocketMessage(InvalidData(detail='The empty text has received.'))
            self.send_json(msg)

    def send_json(self, content=None, close=False):
        if isinstance(content, WebSocketMessage):
            super(AdjustedIndexConsumer, self).send(str(content))
        else:
            super(AdjustedIndexConsumer, self).send(content, close)

    def receive_json(self, content, **kwargs):
        try:

            if content.get('type') == WebSocketMessageType.message.value:
                money = Decimal(content.get('message').get('money'))
                index_id = int(self.scope['url_route']['kwargs']['index_id'])

                try:
                    index = Index.objects.get(pk=index_id)
                except ObjectDoesNotExist:

                    msg = ErrorWebSocketMessage(InvalidData(detail='Index not found'))
                    self.send_json(msg)
                    return

                tickers = index.adjust(money)
                msg = WebSocketMessage(WebSocketMessageType.message.value,
                                       tickers)
                self.send_json(msg)
            else:
                msg = ErrorWebSocketMessage(InvalidMessageType(detail='Unexpected message type'))
                self.send_json(msg)
        except AttributeError as error:
            msg = ErrorWebSocketMessage(FormatError(error))
            self.send_json(msg)

        except InvalidOperation as error:
            msg = ErrorWebSocketMessage(InvalidData(error))
            self.send_json(msg)

    @classmethod
    def encode_json(cls, content):
        return json.dumps(content, cls=ExtendedJSONEncoder)
