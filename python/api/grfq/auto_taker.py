"""
Paradigm asynchronous websocket application which will automatically
create Deribit RFQ and execute quotes for it. You are the Taker.

Usage:
    python3 auto_taker.py [ACCESS KEY] [ACCESS SECRET]

Environment Variables:
    PARADIGM_ACCESS_KEY:       Paradigm Access Key
    PARADIGM_SECRET_KEY:       Paradigm Sceret Key
    PARADIGM_ACCOUNT_NAME_DBT: Deribit account name from admin.test.paradigm.co
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
import sys
import time
import uuid
from urllib.parse import urljoin

import requests
import websockets


try:
    PARADIGM_ACCESS_KEY = sys.argv[1]
    PARADIGM_SECRET_KEY = sys.argv[2]
except IndexError:
    PARADIGM_ACCESS_KEY = None
    PARADIGM_SECRET_KEY = None


SCENARIOS = [
    {
        'legs': [
            {
                'ratio': 1,
                'side': 'BUY',
                'instrument': 'BTC-25MAR22-150000-C',
            },
        ],
        'venue': 'DBT'
    },
    {
        'legs': [
            {
                'ratio': 1,
                'side': 'BUY',
                'instrument': 'BTC-PERPETUAL',
            },
        ],
        'venue': 'DBT',
    },
    {
        'legs': [
            {
                'ratio': 1,
                'side': 'BUY',
                'instrument': 'BTC-PERPETUAL',
            },
            {
                'ratio': 1,
                'side': 'SELL',
                'instrument': 'BTC-25MAR22',
            },
        ],
        'venue': 'DBT',
    },
    {
        'legs': [
            {
                'ratio': 2,
                'side': 'BUY',
                'instrument': 'BTC-25MAR22-150000-C',
            },
            {
                'ratio': 2,
                'side': 'SELL',
                'instrument': 'BTC-24JUN22-200000-C',
            },
            {
                'ratio': 1,
                'side': 'SELL',
                'instrument': 'BTC-30SEP22-300000-C',
            }
        ],
        'venue': 'DBT'
    },
]

WEBSOCKET_CHANNELS = ['rfq', 'quote', 'quote_book', 'trade', 'trade_tape', 'order']

async def main(http_host, ws_url, access_key, secret_key, venue_account_name):
    """
    Opens the websocket connection, creates a RFQ and execute quotes.

    Initially subscribes to all notification channels.
    """
    ws_url += f'?api-key={access_key}&cancel_on_disconnect=false'

    async with websockets.connect(ws_url) as websocket:
        loop = asyncio.get_event_loop()
        # Start the heartbeat thread
        loop.create_task(send_heartbeat(websocket))

        # Subcribe to notification channels
        await subscribe_to_notification_channels(websocket, WEBSOCKET_CHANNELS)

        # Create RFQ for a random strategy
        rfq = create_rfq(
            http_host=http_host,
            access_key=access_key,
            secret_key=secret_key,
            payload=random.choice(SCENARIOS),
        )
        my_rfq_id = rfq['id']
        order_id = None

        while True:
            message = await websocket.recv()
            message = json.loads(message)
            msg_params = message.get('params')

            if not msg_params or 'channel' not in msg_params:
                continue

            channel = msg_params['channel']
            data = msg_params['data']

            if channel in ['trade_tape', 'rfq']:
                continue

            # Check Quotes for your RFQ
            if channel == 'quote_book':
                quote = data['quote']

                if data['kind'] == 'ADDED' and quote['rfq_id'] == my_rfq_id:
                    # Check if quote's price is within custom treshhold
                    # (placeholder)
                    print(f'> Received quote for RFQ({my_rfq_id}): {quote["id"]}')

                    if order_id is None:
                        execution_side = 'BUY' if quote['side'] == 'SELL' else 'SELL'
                        order_payload = {
                            "account": venue_account_name,
                            "client_order_id": str(uuid.uuid4()),
                            "limit_price": quote['price'],
                            "quantity": quote['remaining_quantity'],
                            "execution_side": execution_side,
                        }
                        order = place_order(
                            http_host=http_host,
                            access_key=access_key,
                            secret_key=secret_key,
                            rfq_id=my_rfq_id,
                            payload=order_payload,
                        )
                        order_id = order['id']
                continue

            if channel == 'order':
                order = data['order']
                # Register that the order was placed and is pending
                # settlement (placeholder)
                print(f'> Status for order({order_id}): {order["status"]}')

                if order['status'] == 'CLOSED':
                    # Clean id to restart the quote execution process
                    order_id = None

            if channel == 'trade':
                trade = data['trade']

                if trade['status'] == 'COMPLETED':
                    # Register trade settled (placeholder)
                    print(f'> Trade settled for order({order_id}): {trade["id"]}')
                elif trade['status'] == 'REJECTED':
                    # Register trade failed to settle (placeholder)
                    print(f'> Trade rejected for order({order_id})')


def sign_request(http_host, method, path, payload, access_key, secret_key):
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
    return urljoin(http_host, path), headers, payload


def create_rfq(http_host, access_key, secret_key, payload):
    """
    Creates an RFQ using a random RFQ structure from `SCENARIOS`
    using a signed request.
    """

    method = 'POST'
    path = '/v1/grfq/rfqs/'

    url, headers, payload = sign_request(
        http_host, method, path, payload, access_key, secret_key,
    )
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    print(f'> Created RFQ: {data["id"]}')
    return data


def place_order(http_host, access_key, secret_key, rfq_id, payload):
    """
    Place a new order for a given RFQ.
    """
    method = 'POST'
    path = f'/v1/grfq/rfqs/{rfq_id}/orders/'

    url, headers, payload = sign_request(
        http_host, method, path, payload, access_key, secret_key,
    )
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    print(f'> Placed order for RFQ({rfq_id}): {data["id"]}')
    return data


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
        await asyncio.sleep(5)


async def subscribe_to_notification_channels(websocket, channels):
    """
    Subscribe to websocket channels to receive notifications.
    """
    for index, channel in enumerate(channels):
        print(f'> Subscribed to {channel} channel')
        await websocket.send(json.dumps({
            'id': index + 2, # id=1 for heart beat
            'jsonrpc': '2.0',
            'method': 'subscribe',
            'params': { 'channel': channel }
        }))


if __name__ == '__main__':
    PARADIGM_ACCESS_KEY = os.getenv('PARADIGM_ACCESS_KEY', PARADIGM_ACCESS_KEY)
    PARADIGM_SECRET_KEY = os.getenv('PARADIGM_SECRET_KEY', PARADIGM_SECRET_KEY)
    PARADIGM_ACCOUNT_NAME_DBT = os.getenv('PARADIGM_ACCOUNT_NAME_DBT', 'taker')
    PARADIGM_WS_URL = os.getenv('PARADIGM_WS_URL', 'wss://ws.api.test.paradigm.co/v1/grfq/')
    PARADIGM_HTTP_HOST = os.getenv('PARADIGM_HTTP_HOST', 'https://api.test.paradigm.co')

    try:
        print(f'Paradigm Access Key: {PARADIGM_ACCESS_KEY}')
        print(f'Paradigm Secret Key: {PARADIGM_SECRET_KEY}')
        print(f'Paradigm Account Name - DBT: {PARADIGM_ACCOUNT_NAME_DBT}')
        print(f'Paradigm WS URL: {PARADIGM_WS_URL}')
        print(f'Paradigm HTTP Host: {PARADIGM_HTTP_HOST}')

        # Start the client that opens a websocket connection, creates a
        # RFQ, and executes quotes
        asyncio.get_event_loop().run_until_complete(
            main(
                http_host=PARADIGM_HTTP_HOST,
                ws_url=PARADIGM_WS_URL,
                access_key=PARADIGM_ACCESS_KEY,
                secret_key=PARADIGM_SECRET_KEY,
                venue_account_name=PARADIGM_ACCOUNT_NAME_DBT,
            )
        )

        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print('Error thrown: ', e),
