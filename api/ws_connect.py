#!/usr/bin/env python3
"""
Paradigm websocket test script that connects to the public API websocket
and prints messages it receives.
Keeps the connection alive by sending heartbeat messages on a constant interval.

Usage:
    python3 ws_connect.py --help

Requirements:
    pip3 install click
    pip3 install click-log
    pip3 install websockets
"""

import asyncio
import json
import logging
import pprint

import click
import click_log
import websockets


logger = logging.getLogger(__name__)
click_log.basic_config(logger)


async def receive(host, access_key, log_empty):
    """
    Open the websocket connection and print all received messages.
    Messages with no data are not printed if `log_empty` is not set.
    """
    async with websockets.connect(
            f'{host}/?api-key={access_key}',
    ) as websocket:
        # Start the heartbeat thread
        asyncio.get_event_loop().create_task(send_heartbeat(websocket))

        for channel in ('rfq', 'quote', 'trade', 'trade_confirmation'):
            await websocket.send(json.dumps({
                'id': 123,
                'jsonrpc': '2.0',
                'method': 'subscribe',
                'params': {
                    'channel': channel
                }
            }))
        while True:
            # Receive messages
            message = await websocket.recv()
            has_params = 'params' in message
            if has_params or (log_empty and not has_params):
                logger.debug('> Received: %s', pprint.pprint(json.loads(message)))


async def send_heartbeat(websocket):
    """
    Send a heartbeat message every 5 seconds to keep the connection alive.
    """
    heartbeat_id = 1
    while True:
        await websocket.send(json.dumps({
            'id': heartbeat_id,
            'jsonrpc': '2.0',
            'method': 'heartbeat'
        }))
        heartbeat_id += 1
        await asyncio.sleep(5)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click_log.simple_verbosity_option(logger)
@click.argument('access-key')
@click.option('--host',
              help='The Paradigm API host to send the RFQ to.',
              metavar='HOST', default='wss://ws.api.test.paradigm.co',
              show_default=True)
@click.option('--log-empty',
              help='Log empty messages.',
              default=False, show_default=True,
              )
def start(access_key, host, log_empty):
    # Start the client
    asyncio.get_event_loop().run_until_complete(receive(
        host, access_key, log_empty,
    ))
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    start()
