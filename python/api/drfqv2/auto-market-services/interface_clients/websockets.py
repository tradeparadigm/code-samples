"""
    Venue WebSocket interface client to interact with Paradigm.
"""

# built ins
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional
import os
import time
import base64
import hmac
import json
import logging

# installed
import websockets


class VenueWebSocketClient(ABC):
    def __init__(
        self,
        connection_url: str,
        access_key: str,
        exgest_queue: asyncio.Queue,
        channels_to_subscribe_on_start: List[str]
            ) -> None:
        self.connection_url: str = connection_url
        self.access_key: str = access_key
        self.exgest_queue: asyncio.Queue = exgest_queue
        self.channels_to_subscribe_on_start: List[Tuple[int, str]] = channels_to_subscribe_on_start

        # Instance Variables
        self.url: str = f'{self.connection_url}?api-key={self.access_key}&cancel_on_disconnect=true'
        self.websocket_client: websockets.WebSocketClientProtocol = None
        self.connection_authentication: bool = False

        # Instantiate WebSocket Connection
        asyncio.get_event_loop().create_task(
            self.receiver()
            )

        # Actions on WebSocket Connection
        asyncio.get_event_loop().create_task(
            self.operations_on_websocket_connection()
            )

    @abstractmethod
    def create_operation_payload(
        self,
        ws_operation: str,
        channel: str
            ) -> Dict:
        """
        Creates the Subscribe/Unsubscribe WebSocket
        Operaiton payloads.
        """
        pass

    @abstractmethod
    async def send_heartbeat(self) -> None:
        """
        Sends a Heartbeat to keep the WebSocket connection alive.
        """
        pass

    @abstractmethod
    async def operations_on_websocket_connection(self):
        """
        Operations to instantiate upon the successful
        WebSocket connection.
        """
        pass

    @abstractmethod
    async def initial_ingest_message(
        self,
        message: str
            ) -> Dict:
        """
        Ingest the raw message from the WebSocket
        Interface and determines if it needs to be
        processed further by the system.
        """
        pass

    @abstractmethod
    async def create_send_ws_operation(
        self,
        channel: str,
        operation: str
            ) -> None:
        """
        - Creates the WebSocket payload.
        - Sends the Websocket payload via the WebSocket connection.
        """
        pass

    async def receiver(self) -> None:
        """
        - Instantiates the WebSocket Connection.
        - Receives WebSocket Connection messages.
        - Determines and if the message needs to be processed
        is put on exgestion queue.
        """
        # Instantiate WebSocket Connection
        async with websockets.connect(
            self.url,
            ping_interval=None,
            compression=None
                ) as self.websocket_client:
            while True:
                message: bytes = await self.websocket_client.recv()
                data_message: Dict = await self.initial_ingest_message(
                    message=message
                    )
                if data_message:
                    self.exgest_queue.put_nowait(message)
                await asyncio.sleep(0)

    async def send_payload(
        self,
        payload: Dict
            ) -> None:
        """
        Sends a created WebSocket Payload via the Websocket connection.
        """
        await self.websocket_client.send(
            json.dumps(
                payload
                )
            )


class ParadigmWebSocketClient(VenueWebSocketClient):
    def create_operation_payload(
        self,
        ws_operation: str,
        channel: str
            ) -> Dict:
        """
        Creates the Subscribe/Unsubscribe WebSocket
        Operaiton payloads.
        """
        return {
                "id": 2,
                "jsonrpc": "2.0",
                "method": f"{ws_operation}",
                "params": {
                    "channel": f"{channel}"
                    }
                }

    async def send_heartbeat(self) -> None:
        """
        Sends a Heartbeat to keep the Paradigm WebSocket connection alive.
        """
        while True:
            await self.websocket_client.send(
                json.dumps(
                            {
                                "id": 1,
                                "jsonrpc": "2.0",
                                "method": "heartbeat"
                            }
                            )
                    )
            await asyncio.sleep(5)

    async def operations_on_websocket_connection(self) -> None:
        """
        Operations to instantiate upon the successful
        WebSocket connection.
        """
        while not self.websocket_client:
            await asyncio.sleep(0)

        # Flag connection has been authenticated
        self.connection_authentication = True

        # Instantiate Sending Heartbeat Coroutine
        asyncio.get_event_loop().create_task(
            self.send_heartbeat()
            )

        # Subscribe to Initial WebSocket Channels
        for channel in self.channels_to_subscribe_on_start:
            # Create + Send WS Operation Request
            asyncio.get_event_loop().create_task(
                self.create_send_ws_operation(
                    channel=channel,
                    operation='subscribe'
                    )
                )

    async def initial_ingest_message(
        self,
        message: str
            ) -> Dict:
        """
        Ingest the raw message from the WebSocket
        Interface and determines if it needs to be
        processed further by the system.
        """
        processed_message: Dict = json.loads(message)
        if 'id' not in processed_message:
            return processed_message
        else:
            return {}

    async def create_send_ws_operation(
        self,
        channel: str,
        operation: str
            ) -> None:
        """
        - Creates the WebSocket payload.
        - Sends the Websocket payload via the WebSocket connection.
        """
        while not self.connection_authentication:
            await asyncio.sleep(0)

        # Create Operation Payload
        payload: Dict = self.create_operation_payload(
            channel=channel,
            ws_operation=operation
            )
        # Send WS Operation Request
        asyncio.get_event_loop().create_task(
            self.send_payload(
                payload=payload
                )
            )
