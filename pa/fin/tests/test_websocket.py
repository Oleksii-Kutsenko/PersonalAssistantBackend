"""
WebSocket tests
"""
from decimal import InvalidOperation, Decimal
from unittest import TestCase

from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
import pytest

from fin.exceptions import InvalidData, FormatError, InvalidMessageType
from fin.models import Index
from fin.routing import websocket_urlpatterns
from fin.websocket import ErrorWebSocketMessage, WebSocketMessage, WebSocketMessageType

scope_app = URLRouter(websocket_urlpatterns)


class AdjustedIndexConsumerTestCase(TestCase):

    def setUp(self) -> None:
        self.communicator = None
        self.index = Index.objects.create(data_source_url=Index.Source.SP500)

    async def set_communicator(self, index_id):
        """
        Communicator's setup
        """
        self.communicator = WebsocketCommunicator(scope_app,
                                                  f'/ws/fin/api/indices/{index_id}/adjusted/')
        connected, _ = await self.communicator.connect()
        assert connected

    @pytest.mark.django_db(transaction=True)
    @pytest.mark.asyncio
    async def test_when_receiving_empty_message(self):
        """
        Error expected when empty message has been received
        """
        await self.set_communicator(self.index.id)
        await self.communicator.send_input({"type": "websocket.receive", "text": ''})
        response = await self.communicator.receive_output()

        expected_response = str(
            ErrorWebSocketMessage(InvalidData(detail='The empty text has received.'))
        )

        assert response.get('text') == expected_response

        await self.communicator.disconnect()

    @pytest.mark.django_db(transaction=True)
    @pytest.mark.asyncio
    async def test_when_received_wrong_number(self):
        """
        Error expected when the money parameter cannot be converted to decimal
        """
        await self.set_communicator(self.index.id)

        wrong_number = '2000q'
        msg = str(WebSocketMessage(WebSocketMessageType.message.value,
                                   {'money': wrong_number}))

        await self.communicator.send_to(msg)
        response = await self.communicator.receive_from()

        try:
            Decimal(wrong_number)
        except InvalidOperation as error:
            expected_response = str(ErrorWebSocketMessage(InvalidData(error)))

            assert response == expected_response

    @pytest.mark.django_db(transaction=True)
    @pytest.mark.asyncio
    async def test_when_received_wrong_json(self):
        """
        Error expected when json is valid and when internal protocol is violated
        """
        await self.set_communicator(self.index.id)

        wrong_message = []

        await self.communicator.send_to(str(wrong_message))
        response = await self.communicator.receive_from()

        try:
            wrong_message.get('type')
        except AttributeError as error:
            expected_response = str(ErrorWebSocketMessage(FormatError(error)))

            assert response == expected_response

    @pytest.mark.django_db(transaction=True)
    @pytest.mark.asyncio
    async def test_when_requesting_not_existing_index(self):
        """
        Error expected when requesting a not existing index
        """
        await self.set_communicator(self.index.id + 1)

        money = 1000
        msg = str(WebSocketMessage(WebSocketMessageType.message.value,
                                   {'money': money}))

        await self.communicator.send_to(msg)
        response = await self.communicator.receive_from()

        expected_response = str(ErrorWebSocketMessage(InvalidData(detail='Index not found')))

        assert response == expected_response

    @pytest.mark.django_db(transaction=True)
    @pytest.mark.asyncio
    async def test_when_received_right_msg(self):
        """
        Correct response expected
        """
        await self.set_communicator(self.index.id)

        money = 1000
        msg = str(WebSocketMessage(WebSocketMessageType.message.value,
                                   {'money': money}))

        await self.communicator.send_to(msg)
        response = await self.communicator.receive_from()

        expected_msg = str(WebSocketMessage(WebSocketMessageType.message.value,
                                            await database_sync_to_async(self.index.adjust)(money)))

        assert response == expected_msg

    @pytest.mark.django_db(transaction=True)
    @pytest.mark.asyncio
    async def test_when_received_wrong_message(self):
        """
        Informational message type expected
        """
        await self.set_communicator(self.index.id)

        msg = str(WebSocketMessage(WebSocketMessageType.error.value,
                                   {'': None}))

        await self.communicator.send_to(msg)
        response = await self.communicator.receive_from()

        expected_msg = str(
            ErrorWebSocketMessage(InvalidMessageType(detail='Unexpected message type')))

        assert response == expected_msg
