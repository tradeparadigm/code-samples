"""
Paradigm asynchronous websocket application which will automatically
create Deribit RFQs and send them to a designated Maker. You are the Taker.

Usage:
    python3 auto_taker.py [ACCESS KEY] [ACCESS SECRET]

Environment Variables:
    PARADIGM_ACCESS_KEY:       Paradigm Access Key
    PARADIGM_SECRET_KEY:       Paradigm Sceret Key
    PARADIGM_ACCOUNT_NAME_DBT: Deribit account name from admin.test.paradigm.co
    MAKER_DESK_NAME:           Maker Desk Name
    PARADIGM_WS_URL:           Paradigm WS URL
    PARADIGM_HTTP_HOST:        Paradigm HTTP Host

Requirements:
    pip3 install requests websockets
"""

import asyncio
import base64
import hmac
import os
import json
import pprint
import random
import requests
import sys
import time
from urllib.parse import urljoin

import websockets


try:
    PARADIGM_ACCESS_KEY = sys.argv[1]
    PARADIGM_SECRET_KEY = sys.argv[2]
except IndexError:
    PARADIGM_ACCESS_KEY = None
    PARADIGM_SECRET_KEY = None

RFQ_CREATE_SECONDS = 10

SCENARIOS = [
    {
        'anonymous': True,
        'expires_in': 120,
        'legs': [
            {
                'quantity': 20000,
                'side': 'BUY',
                'instrument': 'BTC-PERPETUAL',
                'venue': 'DBT',
            },
        ]
    },
    {
        'expires_in': 80,
        'legs': [
            {
                'quantity': 15000,
                'side': 'BUY',
                'instrument': 'BTC-PERPETUAL',
                'venue': 'DBT',
            },
            {
                'quantity': 15000,
                'side': 'SELL',
                'instrument': 'BTC-26MAR21',
                'venue': 'DBT',
            },
        ]
    },
    {
        'expires_in': 60,
        'legs': [
            {
                'quantity': 50000,
                'side': 'BUY',
                'instrument': 'BTC-26MAR21',
                'venue': 'DBT',
            },
            {
                'quantity': 50000,
                'side': 'SELL',
                'instrument': 'BTC-PERPETUAL',
                'venue': 'DBT',
            },
        ]
    },
    {
        'expires_in': 60,
        'legs': [
            {
                'quantity': 45000,
                'side': 'SELL',
                'instrument': 'BTC-PERPETUAL',
                'venue': 'DBT',
            },
            {
                'quantity': 45000,
                'side': 'BUY',
                'instrument': 'BTC-25JUNE21',
                'venue': 'DBT',
            },
        ]
    },
    {
        'expires_in': 65,
        'legs': [
            {
                'quantity': 25,
                'side': 'BUY',
                'instrument': 'BTC-8JAN21-22000-C',
                'venue': 'DBT',
            },
        ]
    },
    {
        'expires_in': 65,
        'legs': [
            {
                'quantity': 12.5,
                'side': 'BUY',
                'instrument': 'BTC-8JAN21-22000-C',
                'venue': 'DBT',
            },
            {
                'quantity': 12.5,
                'side': 'SELL',
                'instrument': 'BTC-29JAN21-18000-C',
                'venue': 'DBT',
            },
        ]
    },
    {
        'expires_in': 65,
        'legs': [
            {
                'quantity': 12.5,
                'side': 'BUY',
                'instrument': 'BTC-8JAN21-22000-C',
                'venue': 'DBT'
            },
            {
                'quantity': 12.5,
                'side': 'SELL',
                'instrument': 'BTC-29JAN21-18000-C',
                'venue': 'DBT'
            },
            {
                'quantity': 5,
                'side': 'SELL',
                'instrument': 'BTC-29JAN21-18000-P',
                'venue': 'DBT'
            }
        ]
    },
    {
        'expires_in': 65,
        'legs': [
            {
                'quantity': 12.5,
                'side': 'BUY',
                'instrument': 'BTC-8JAN21-22000-C',
                'venue': 'DBT'
            },
            {
                'quantity': 12.5,
                'side': 'SELL',
                'instrument': 'BTC-29JAN21-18000-C',
                'venue': 'DBT'
            },
            {
                'quantity': 15,
                'side': 'SELL',
                'instrument': 'BTC-29JAN21-18000-P',
                'venue': 'DBT'
            },
            {
                'quantity': 50,
                'side': 'SELL',
                'instrument': 'BTC-29JAN21-15000-C',
                'venue': 'DBT'
            },
            {
                'quantity': 6,
                'side': 'SELL',
                'instrument': 'BTC-26MAR21-20000-P',
                'venue': 'DBT'
            },
            {
                'quantity': 63,
                'side': 'SELL',
                'instrument': 'BTC-25JUN21-20000-C',
                'venue': 'DBT'
            }
        ]
    },
]


async def main(http_host, ws_url, access_key, secret_key, maker_desk_ticker,
               account_info):
    """
    Opens the websocket connection and starts creating RFQs.

    Initially subscribes to all notification channels.
    """
    async with websockets.connect(
        f'{ws_url}?api-key={access_key}&cancel_on_disconnect=false',
    ) as websocket:
        loop = asyncio.get_event_loop()
        # Start the heartbeat thread
        loop.create_task(send_heartbeat(websocket))

        # Subcribe to RFQ Notification Channel
        await subscribe_rfq_notification(websocket)
        # Subcribe to Quote Notification Channel
        await subscribe_quote_notifcation(websocket)
        # Subcribe to Trade Notification Channel
        await subscribe_trade_notifcation(websocket)
        # Subcribe to Trade_Confirmation Notification Channel
        await subscribe_tradeconfirmation_notifcation(websocket)

        # Create RFQ Task that randomly sends out scenarios
        loop.create_task(create_rfq_task(
            http_host=http_host,
            access_key=access_key,
            secret_key=secret_key,
            maker_desk_ticker=maker_desk_ticker,
            account_info=account_info,
        ))

        while True:
            message = await websocket.recv()
            message = json.loads(message)
            if 'params' in message:
                if 'channel' in message['params'].keys():
                    print('> Received on channel %s:' % message['params']['channel'])
                    pprint.pprint(message['params']['data'])


async def create_rfq_task(http_host, access_key, secret_key, maker_desk_ticker,
                          account_info):
    """
    Task that continually runs and creates an RFQ every `RFQ_CREATE_SECONDS` seconds
    using a random config from `SCENARIOS`.
    """
    while True:
        await asyncio.sleep(5)
        random_client_order_id = int(time.time())
        scenario_base_payload = {
            'account': {
                'name': account_info['name']['DBT']
            },
            'anonymous': False,
            'client_order_id': random_client_order_id,
            'counterparties': [maker_desk_ticker],
        }

        payload = scenario_base_payload | random.choice(SCENARIOS)
        await create_rfq(http_host, access_key, secret_key, payload)
        print('> Created RFQ: ')
        pprint.pprint(payload)
        await asyncio.sleep(RFQ_CREATE_SECONDS)


async def create_rfq(http_host, access_key, secret_key, payload):
    """
    Creates an RFQ using a signed request.
    """

    method = 'POST'
    path = '/rfq/create/'

    body = json.dumps(payload).encode('utf-8')

    message = method.encode('utf-8') + b'\n'
    message += path.encode('utf-8') + b'\n'
    message += body

    timestamp = str(int(time.time() * 1000))
    message = timestamp.encode('utf-8') + b'\n' + message
    signing_key = base64.b64decode(secret_key)
    digest = hmac.digest(signing_key, message, 'sha256')
    signature = base64.b64encode(digest)

    headers = {
        'Paradigm-API-Timestamp': timestamp,
        'Paradigm-API-Signature': signature,
        'Authorization': f'Bearer {access_key}'
    }

    response = requests.post(urljoin(http_host, path), headers=headers, json=payload)
    return response


# Heartbeat Function
async def send_heartbeat(websocket):
    """
    Send a heartbeat message to keep the connection alive.
    """
    while True:
        await websocket.send(json.dumps({
            'id': 1,
            'jsonrpc': '2.0',
            'method': 'heartbeat'
        }))
        await asyncio.sleep(1)


# Subscription Channel Functions
async def subscribe_rfq_notification(websocket):
    """
    Subscribe to the RFQ Channel to receive rfq notifications.
    """
    print('> Subscribed to RFQ Channel')
    await websocket.send(json.dumps({
        'id': 2,
        'jsonrpc': '2.0',
        'method': 'subscribe',
        'params': {
            'channel': 'rfq'
        }
    }))


async def subscribe_quote_notifcation(websocket):
    """
    Subscribe to the Quote Channel to receive quote notifications.
    """
    print('> Subscribed to Quote Channel')
    await websocket.send(json.dumps({
        'id': 3,
        'jsonrpc': '2.0',
        'method': 'subscribe',
        'params': {
            'channel': 'quote'
        }
    }))


async def subscribe_trade_notifcation(websocket):
    """
    Subscribe to the Trade Channel to receive trade notifications.
    """
    print('> Subscribed to Trade Channel')
    await websocket.send(json.dumps({
        'id': 4,
        'jsonrpc': '2.0',
        'method': 'subscribe',
        'params': {
            'channel': 'trade'
        }
    }))


async def subscribe_tradeconfirmation_notifcation(websocket):
    """
    Subscribe to the Trade Confirmation Channel to receive trade_confirmation notifications.
    """
    print('> Subscribed to Trade Confirmation Channel')
    await websocket.send(json.dumps({
        'id': 5,
        'jsonrpc': '2.0',
        'method': 'subscribe',
        'params': {
            'channel': 'trade_confirmation'
        }
    }))


if __name__ == '__main__':
    PARADIGM_ACCESS_KEY = os.getenv(
        'PARADIGM_ACCESS_KEY', PARADIGM_ACCESS_KEY,
    )
    PARADIGM_SECRET_KEY = os.getenv(
        'PARADIGM_SECRET_KEY', PARADIGM_SECRET_KEY,
    )
    PARADIGM_ACCOUNT_NAME_DBT = os.getenv('PARADIGM_ACCOUNT_NAME_DBT')
    MAKER_DESK_TICKER = os.getenv('MAKER_DESK_TICKER')
    PARADIGM_WS_URL = os.getenv('PARADIGM_WS_URL', 'wss://ws.api.test.paradigm.co/')
    PARADIGM_HTTP_HOST = os.getenv('PARADIGM_HTTP_HOST', 'https://api.test.paradigm.co')

    paradigm_account_information = {
        'name': {
            'DBT': PARADIGM_ACCOUNT_NAME_DBT,
        }
    }

    try:
        print(f'Paradigm Account Name - DBT: {PARADIGM_ACCESS_KEY}')
        print(f'Paradigm Account Name - DBT: {PARADIGM_SECRET_KEY}')
        print(f'Paradigm Account Name - DBT: {PARADIGM_ACCOUNT_NAME_DBT}')
        print(f'Maker Desk Name: {MAKER_DESK_TICKER}')
        print(f'Paradigm WS URL: {PARADIGM_WS_URL}')
        print(f'Paradigm HTTP Host: {PARADIGM_HTTP_HOST}')

        # Start the client that opens a websocket connection and creates RFQs
        asyncio.get_event_loop().run_until_complete(
            main(
                http_host=PARADIGM_HTTP_HOST,
                ws_url=PARADIGM_WS_URL,
                access_key=PARADIGM_ACCESS_KEY,
                secret_key=PARADIGM_SECRET_KEY,
                maker_desk_ticker=MAKER_DESK_TICKER,
                account_info=paradigm_account_information,
            )
        )

        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print('Error thrown: ', e)
