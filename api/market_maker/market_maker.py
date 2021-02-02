"""
Paradigm asynchronous websocket application to automatically respond with
random prices from the exchange's instrument's mark price. You are the maker.

Usage:
    python3 market_maker.py [ACCESS KEY] [ACCESS SECRET]

Environment Variables:
    PARADIGM_ACCESS_KEY:       Paradigm Access Key
    PARADIGM_SECRET_KEY:       Paradigm Sceret Key
    PARADIGM_ACCOUNT_NAME_DBT: Paradigm Account Name - DBT
    PARADIGM_ACCOUNT_NAME_BIT: Paradigm Account Name - BIT
    PARADIGM_ACCOUNT_NAME_CME: Paradigm Account Name - CME
    DBT_HTTP_HOST:             HTTP Host - DBT
    BIT_HTTP_HOST:             HTTP Host - BIT
    PARADIGM_WS_URL:           Paradigm WS URL
    PARADIGM_HTTP_HOST:        Paradigm HTTP Host

Requirements:
    pip3 install requests websockets
"""

import asyncio
import base64
import decimal
import hmac
import json
import os
import random
import sys
import time
from random import randint
from urllib.parse import urljoin

import requests
import websockets

BUY = 'BUY'
SELL = 'SELL'

try:
    PARADIGM_ACCESS_KEY = sys.argv[1]
    PARADIGM_SECRET_KEY = sys.argv[2]
except IndexError:
    PARADIGM_ACCESS_KEY = None
    PARADIGM_SECRET_KEY = None


async def main(access_key, secret_key, paradigm_account_information,
               paradigm_ws_url, dbt_http_host, bit_http_host,
               paradigm_http_host, min_tick_size):
    """
    Connect to the websocket and respond to RFQs with quotes as they come in.
    Initially subscribe to all notification channels.
    """
    async with websockets.connect(f'{paradigm_ws_url}?api-key={access_key}') as websocket:
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

        while True:
            message = await websocket.recv()
            message = json.loads(message)
            if 'params' in message:
                if 'channel' in message['params'].keys():
                    if message['params']['channel'] == 'rfq':
                        rfq_details = message['params']['data']

                        if message['params']['data']['status'] == 'ACTIVE':
                            # Do not offer a Quote if the venue is CME
                            if rfq_details['legs'][0]['venue'] == 'CME':
                                continue
                            # Respond with a buy and a sell Quote to every RFQ
                            for side in [BUY, SELL]:
                                response = await quote_rfq(rfq_details, min_tick_size,
                                                           dbt_http_host, bit_http_host,
                                                           access_key, secret_key,
                                                           paradigm_http_host,
                                                           paradigm_account_information,
                                                           side)
                                if response.status_code == 200:
                                    response_json = json.loads(response.text)
                                    print('Successfully Quoted')
                                    print(f"response_json: {type(response_json)}, {response_json}")
                                    print('RFQ_ID: {}'.format(response_json['rfq_id']))
                                    print('QUOTE_ID: {}'.format(response_json['quote_id']))


# Quote Create Functions
async def quote_rfq(rfq_details, min_tick_size, dbt_http_host, bit_http_host,
                    access_key, secret_key, paradigm_http_host,
                    account_information, side):
    """
    Call the construct quote function as well
    as create the required HTTP signature.
    """

    method = 'POST'
    path = '/quote/create/'

    data = construct_rfq_quote_data(rfq_details, min_tick_size, dbt_http_host,
                                    bit_http_host, account_information, side)
    body = json.dumps(data).encode('utf-8')

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

    response = requests.post(urljoin(paradigm_http_host, path), headers=headers, json=data)
    return response


def construct_rfq_quote_data(rfq_details, min_tick_size, dbt_http_host,
                             bit_http_host, account_information, side):
    """
    Create Quote payload.
    """
    client_order_id = f'{randint(1, 1000000000)}'
    quote_legs = []
    for leg in rfq_details['legs']:
        quote_leg = {}
        venue = leg['venue']
        quote_leg['instrument'] = leg['instrument']
        quote_leg['side'] = leg['side']
        quote_leg['venue'] = venue
        quote_leg['quantity'] = leg['quantity']
        if 'price' in leg:
            quote_leg['price'] = leg['price']
        else:
            mark = get_mark_price(venue, leg['instrument'], dbt_http_host, bit_http_host)
            bid, offer = get_bid_and_ask_price(venue, leg['instrument'], mark, min_tick_size)
            if side == BUY:
                quote_leg['price'] = offer
            else:
                quote_leg['price'] = bid
        quote_legs.append(quote_leg)

    data = {
        'account': {
            'name': account_information['name'][venue]
        },
        'client_order_id': client_order_id,
        'expires_in': randint(60, 120),
        'legs': quote_legs,
        'rfq_id': rfq_details['rfq_id'],
        'side': side,
    }
    return data


def get_mark_price(venue, instrument, dbt_http_host, bit_http_host):
    """
    Fetch current mark price for the instrument.
    """
    if venue == 'DBT':
        return get_dbt_mark_price(instrument, dbt_http_host)
    if venue == 'BIT':
        return get_bit_mark_price(instrument, bit_http_host)


def get_dbt_mark_price(instrument, http_host):
    """
    Get ticker details from venue DBT and returns mark price.
    """
    uri = http_host + f'/public/ticker?instrument_name={instrument}'
    response = requests.get(url=uri)
    result = response.json()['result']
    return result['mark_price']


def get_bit_mark_price(instrument, http_host):
    """
    Get ticker details from venue BIT and returns mark price.
    """
    uri = f'{http_host}/tickers?instrument_id={instrument}'
    response = requests.get(url=uri)
    result = response.json()['data']
    return result['mark_price']


def get_bid_and_ask_price(venue, instrument, mark_price, min_tick_size):
    """
    Returns bid and ask price calculated based on
    mark price and randomised offset.
    """
    mark_price = int(mark_price) if float(mark_price).is_integer() else float(mark_price)

    if instrument[-1] == 'C' or instrument[-1] == 'P':
        offset = random.uniform(0, 3)
    elif venue == 'BIT' and instrument[-1] == 'F':
        offset = random.uniform(0, 0.5)
    elif venue == 'BIT' and instrument[-1] == 'L':
        offset = random.uniform(0, 0.5)
    else:
        offset = 1
    bid = mark_price * (1 - offset / 100)
    ask = mark_price * (1 + offset / 100)
    min_tick = get_min_tick_size(venue, instrument, min_tick_size)
    bid = round_price(bid, min_tick)
    ask = round_price(ask, min_tick)
    return (bid, ask) if mark_price > 0 else (ask, bid)


def get_min_tick_size(venue, instrument, min_tick_size):
    """Get minimum quote tick size for the instrument"""
    asset = instrument.split('-')[0]
    inst_type = 'OPTION' if (instrument[-1] == 'C' or instrument[-1] == 'P') else 'FUTURE'
    return min_tick_size[venue][asset][inst_type]


def round_price(price, min_tick):
    """
    Round input price to a given instrument's
    minimum tick size and precision.
    """
    tick_size = min_tick
    precision = decimal.Decimal(str(min_tick)).as_tuple().exponent * -1
    price = round(round(price / tick_size) * tick_size, precision)
    # format price to remove trailing zeroes
    price = int(price) if price % 1 == 0 else price
    return price


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
    PARADIGM_ACCOUNT_NAME_BIT = os.getenv('PARADIGM_ACCOUNT_NAME_BIT')
    PARADIGM_ACCOUNT_NAME_CME = os.getenv('PARADIGM_ACCOUNT_NAME_CME')

    DBT_HTTP_HOST = os.getenv(
        'DBT_HTTP_HOST', 'https://test.deribit.com/api/v2',
    )
    BIT_HTTP_HOST = os.getenv(
        'BIT_HTTP_HOST', 'https://testapi.bitexch.dev/v1',
    )
    PARADIGM_WS_URL = os.getenv('PARADIGM_WS_URL', 'wss://ws.api.test.paradigm.co/')
    PARADIGM_HTTP_HOST = os.getenv('PARADIGM_HTTP_HOST', 'https://api.test.paradigm.co')

    paradigm_account_information = {
        'name': {
            'DBT': PARADIGM_ACCOUNT_NAME_DBT,
            'BIT': PARADIGM_ACCOUNT_NAME_BIT,
            'CME': PARADIGM_ACCOUNT_NAME_CME
        }
    }

    # Minimum Tick Size
    MIN_TICK_SIZE = {
        'DBT': {
            'BTC': {'OPTION': 0.0001, 'FUTURE': 0.01},
            'ETH': {'OPTION': 0.0001, 'FUTURE': 0.01}},
        'BIT': {
            'BTC': {'OPTION': 0.0001, 'FUTURE': 0.5},
        },
    }

    try:
        print(f'Paradigm Account Name - DBT: {PARADIGM_ACCOUNT_NAME_DBT}')
        print(f'Paradigm Account Name - BIT: {PARADIGM_ACCOUNT_NAME_BIT}')
        print(f'Paradigm Account Name - CME: {PARADIGM_ACCOUNT_NAME_CME}')
        print(f'HTTP Host - DBT: {DBT_HTTP_HOST}')
        print(f'HTTP Host - BIT: {BIT_HTTP_HOST}')
        print(f'Paradigm WS URL: {PARADIGM_WS_URL}')
        print(f'Paradigm HTTP Host: {PARADIGM_HTTP_HOST}')
        # Start the client
        asyncio.get_event_loop().run_until_complete(
            main(
                access_key=PARADIGM_ACCESS_KEY,
                secret_key=PARADIGM_SECRET_KEY,
                paradigm_account_information=paradigm_account_information,
                dbt_http_host=DBT_HTTP_HOST,
                bit_http_host=BIT_HTTP_HOST,
                paradigm_ws_url=PARADIGM_WS_URL,
                paradigm_http_host=PARADIGM_HTTP_HOST,
                min_tick_size=MIN_TICK_SIZE,
            )
        )

        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print('Local Main Error')
        print(e)
