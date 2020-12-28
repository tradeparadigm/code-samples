#!/usr/bin/env python3
"""
Paradigm websocket test script that connects to the public API websocket
and prints messages it receives.
Keeps the connection alive by sending heartbeat messages on a constant interval.

Usage:
    python3 ws.test.py [API key]

Requirements:
    pip3 install websockets
"""

import asyncio
import json
import pprint
import sys

import websockets


# Change to False to print heartbeat response messages
DISABLE_HEARTBEAT_PRINT = True

WS_URL = 'wss://ws.api.test.paradigm.co/'

# API key from the first command line arg
api_key = sys.argv[1]


async def receive():
    """
    Open the websocket connection and print all received messages.
    Messages with no data are not printed if DISABLE_HEARTBEAT_PRINT is set.
    """
    async with websockets.connect(
            f'{WS_URL}?api-key={api_key}',
    ) as websocket:
        # Start the heartbeat thread
        asyncio.get_event_loop().create_task(send_heartbeat(websocket))

        for channel in ('rfq', 'quote', 'trade', 'trade_confirmation'):
            await websocket.send(json.dumps({
                "id": 123,
                "jsonrpc": "2.0",
                "method": "subscribe",
                "params": {
                    "channel": channel
                }
            }))
        while True:
            # Receive messages
            message = await websocket.recv()
            if DISABLE_HEARTBEAT_PRINT and 'params' not in message:
                # Don't print heart response message with no data
                continue

            print('> Received:')
            pprint.pprint(json.loads(message))


async def send_heartbeat(websocket):
    """
    Send a heartbeat message to keep the connection alive.
    """
    heartbeat_id = 1
    while True:
        await websocket.send(json.dumps({
            "id": heartbeat_id,
            "jsonrpc": "2.0",
            "method": "heartbeat"
        }))
        heartbeat_id += 1
        await asyncio.sleep(5)


# Start the client
asyncio.get_event_loop().run_until_complete(receive())
asyncio.get_event_loop().run_forever()
