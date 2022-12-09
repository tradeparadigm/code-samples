"""
Description:
    Paradigm WebSocket Asyncio Example.

    Product: DRFQv2

Usage:
    python3.9 paradigm-drfqv2-ws-example.py

Requirements:
    - websocket-client >= 1.2.1
"""

# built ins
import asyncio
import sys
import json
import logging
from typing import Dict

# installed
import websockets


class main:
    def __init__(
        self,
        ws_connection_url: str,
        access_key: str
            ) -> None:
        # Async Event Loop
        self.loop = asyncio.get_event_loop()

        # Instance Variables
        self.ws_connection_url: str = ws_connection_url + f'?api-key={access_key}'
        self.access_key: str = access_key
        self.websocket_client: websockets.WebSocketClientProtocol = None

        # Start Primary Coroutine
        self.loop.run_until_complete(
            self.ws_manager()
            )

    async def ws_manager(self) -> None:
        async with websockets.connect(
            self.ws_connection_url,
            ping_interval=None,
            compression=None,
            close_timeout=60
            ) as self.websocket_client:

            # Maintain Heartbeat
            self.loop.create_task(
                self.maintain_heartbeat()
                )

            # Subscribe to the specified WebSocket Channel
            self.loop.create_task(
                self.ws_operation(
                    operation='subscribe',
                    ws_channel='rfqs'
                    )
                )

            while self.websocket_client.open:
                message: bytes = await self.websocket_client.recv()
                message: Dict = json.loads(message)
                logging.info(message)

            else:
                logging.info('WebSocket connection has broken.')
                sys.exit(1)

    async def ws_operation(
        self,
        operation: str,
        ws_channel: str
            ) -> None:
        """
        `subscribes` or `unsubscribes` to the
        specified WebSocket Channel.
        """
        msg: Dict = {
                    "id": 2,
                    "jsonrpc": "2.0",
                    "method": operation,
                    "params": {
                        "channel": ws_channel
                            }
                        }

        await self.websocket_client.send(
            json.dumps(
                msg
                )
            )

    async def maintain_heartbeat(self) -> None:
        """
        Send a heartbeat message to keep the connection alive.
        """
        msg: Dict = json.dumps(
                {
                    "id": 10,
                    "jsonrpc": "2.0",
                    "method": "heartbeat"
                }
            )

        while True:
            await self.websocket_client.send(msg)

            await asyncio.sleep(9)


if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level='INFO',
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Paradigm LIVE WebSocket Connection URL
    # ws_connection_url: str = 'wss://ws.api.prod.paradigm.trade'
    # Paradigm TEST WebSocket Connection URL
    ws_connection_url: str = 'wss://ws.api.testnet.paradigm.trade'

    # FSPD Version + Product URL
    ws_connection_url += '/v2/drfq'

    # Paradigm Access Key
    access_key: str = '<access-key>'

    main(
         ws_connection_url=ws_connection_url,
         access_key=access_key
         )
