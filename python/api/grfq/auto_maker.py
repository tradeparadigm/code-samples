"""
Paradigm asynchronous websocket application which will automatically
send quotes to incoming Deribit RFQs. You are the Maker.

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

WEBSOCKET_CHANNELS = ['rfq', 'quote', 'quote_book', 'trade', 'trade_tape', 'order']


async def main(http_host, ws_url, access_key, secret_key, venue_account_name):
    """
    Opens the websocket connection and sends quotes to incoming RFQs.

    Initially subscribes to all notification channels.
    """
    ws_url += f'?api-key={access_key}&cancel_on_disconnect=false'

    async with websockets.connect(ws_url) as websocket:
        loop = asyncio.get_event_loop()
        # Start the heartbeat thread
        loop.create_task(send_heartbeat(websocket))

        # Subcribe to notification channels
        await subscribe_to_notification_channels(websocket, WEBSOCKET_CHANNELS)

        my_quotes = []

        print('> Waiting for RFQs...')

        while True:
            message = await websocket.recv()
            message = json.loads(message)
            msg_params = message.get('params')

            if not msg_params or 'channel' not in msg_params:
                continue

            channel = msg_params['channel']
            data = msg_params['data']

            if channel in ['quote_book', 'trade_tape']:
                continue

            if channel == 'rfq' and data['kind'] == 'ADDED':
                rfq = data['rfq']

                if rfq['venue'] != 'DBT':
                    continue

                rfq_id = rfq['id']
                print(f'> New RFQ notification received: {rfq_id})')

                # Quote RFQ (placeholder)
                quote = quote_rfq(
                    http_host=http_host,
                    access_key=access_key,
                    secret_key=secret_key,
                    rfq_id=rfq_id,
                    venue_account_name=venue_account_name,
                )
                my_quotes.append(quote['id'])

            if channel == 'order':
                order = data['order']
                # Register that the order was placed and is pending
                # settlement (placeholder)
                print(f'> Status for order({order["id"]}): {order["status"]}')

            if channel == 'trade':
                trade = data['trade']
                order_id = trade["order_id"]

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


def get_bbo(http_host, access_key, secret_key, rfq_id):
    """
    Fetch RFQ best bid/offer prices
    """

    method = 'GET'
    path = f'/v1/grfq/rfqs/{rfq_id}/bbo/'

    payload = {}

    url, headers, payload = sign_request(
        http_host, method, path, payload, access_key, secret_key,
    )
    response = requests.get(url, headers=headers, json=payload)
    print(f'> Fetched bbo for RFQ({rfq_id})')

    return response.json()


def post_quote(http_host, access_key, secret_key, rfq_id, payload):
    """
    Send a quote to a given RFQ.
    """
    method = 'POST'
    path = f'/v1/grfq/rfqs/{rfq_id}/quotes/'

    url, headers, payload = sign_request(
        http_host, method, path, payload, access_key, secret_key,
    )
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    print(f'> Quoted RFQ({rfq_id}): {data["id"]}')
    return data


def quote_rfq(http_host, access_key, secret_key, rfq_id, venue_account_name):
    """
    Build the quote payload and post it to the RFQ.
    """
    bbo = get_bbo(
        http_host=http_host,
        access_key=access_key,
        secret_key=secret_key,
        rfq_id=rfq_id,
    )

    quote_side = random.choice(['BUY', 'SELL'])
    quote_legs = []

    for leg_bbo in bbo['leg_prices']:
        price_attr = 'best_bid_price' if quote_side == 'BUY' else 'best_ask_price'
        quote_legs.append({
            'instrument': leg_bbo['instrument'],
            'price': leg_bbo[price_attr]
        })

    quote_payload = {
        'account': venue_account_name,
        'client_order_id': str(uuid.uuid4()),
        'quantity': '25',
        'side': quote_side,
        'legs': quote_legs,
        'post_only': False,
    }

    return post_quote(
        http_host=http_host,
        access_key=access_key,
        secret_key=secret_key,
        rfq_id=rfq_id,
        payload=quote_payload,
    )


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
