"""
Paradigm asynchronous websocket application which will automatically respond
with random prices from the exchange's instrument's mark price. You are the MM.

Usage:
    python3 market-maker.py

Environment Variables:
    Paradigm Access Key
    Paradigm Sceret Key
    Paradigm Account Name - DBT
    Paradigm Account Name - BIT
    Paradigm Account Name - CME
    Paradigm Desk Name
    HTTP Host - DBT
    HTTP Host - BIT
    Paradigm WS URL
    Paradigm HTTP Host

Requirements:
    pip3 install websockets
    pip3 install requests
"""

# built ins
import os
import sys
import json
import base64
from random import randint, choice
import random
import hmac
import time
from urllib.parse import urljoin
import asyncio
import decimal
import traceback
import argparse

# installed
import websockets
import requests


# Main Function
async def main(access_key, secret_key, paradigm_account_information,
               paradigm_ws_url, dbt_http_host, bit_http_host,
               paradigm_http_host, min_tick_size):
    """
    Primary async function.
    Initially subscribe to all notification channels.
    """
    async with websockets.connect(f"{paradigm_ws_url}?api-key={access_key}") as websocket:
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

        global previous_quotes_dict
        previous_quotes_dict = {}

        while True:
            try:
                message = await websocket.recv()
            except:
                print('Reconnecting')
                websocket = await websockets.connect(paradigm_ws_url)
            message = json.loads(message)
            # print(f"> {message}")
            if 'params' in message:
                if 'channel' in message['params'].keys():
                    if message['params']['channel'] == 'rfq':
                        # print('> Incoming RFQ')
                        rfq_details = message['params']['data']
                        # print(f"> {rfq_details}")

                        if message['params']['data']['status'] == 'ACTIVE':
                            # Do not offer a Quote if the venue is CME
                            if rfq_details['legs'][0]['venue'] == 'CME':
                                continue

                            # Respond with a two-way Quote to every RFQ
                            sides_list = ['BUY', 'SELL']
                            first_side = choice(sides_list)
                            second_side = 'SELL' if first_side == 'BUY' else 'BUY'
                            # First side
                            response = await quote_rfq(rfq_details, min_tick_size,
                                                       dbt_http_host, bit_http_host,
                                                       access_key, secret_key,
                                                       paradigm_http_host, first_side)
                            if response.status_code == 200:
                                print('Successfully Quoted')
                                response_json = json.loads(response.text)
                                print('RFQ_ID: {}'.format(response_json['rfq_id']))
                                print('QUOTE_ID: {}'.format(response_json['quote_id']))
                            else:
                                print('Attempted to Quote but Failed')
                                print('RFQ_ID: {}'.format(message['params']['data']['rfq_id']))
                                print('RFQ Details:')
                                print(message['params']['data'])
                                print('/quote/create/ Response Status Code: {}'.format(response.status_code))
                                print('/quote/create/ Response Text: {}'.format(response.text))
                            await asyncio.sleep(1.5)
                            # Second side
                            response = await quote_rfq(rfq_details, min_tick_size,
                                                       dbt_http_host, bit_http_host,
                                                       access_key, secret_key,
                                                       paradigm_http_host, second_side)
                            if response.status_code == 200:
                                print('Successfully Quoted')
                                response_json = json.loads(response.text)
                                print('RFQ_ID: {}'.format(response_json['rfq_id']))
                                print('QUOTE_ID: {}'.format(response_json['quote_id']))
                            else:
                                print('Attempted to Quote but Failed')
                                print('RFQ_ID: {}'.format(message['params']['data']['rfq_id']))
                                print('RFQ Details:')
                                print(message['params']['data'])
                                print('/quote/create/ Response Status Code: {}'.format(response.status_code))
                                print('/quote/create/ Response Text: {}'.format(response.text))

# Quote Create Functions
async def quote_rfq(rfq_details, min_tick_size,
                    dbt_http_host, bit_http_host,
                    access_key, secret_key,
                    paradigm_http_host, side):
    """
    Call the construct quote function as well
    as create the required HTTP signature.
    """

    method = 'POST'
    path = '/quote/create/'

    data = construct_rfq_quote_data(rfq_details, min_tick_size,
                                    dbt_http_host, bit_http_host,
                                    side)
    # print('> Quote/Create Request Data: \n', data)
    body = json.dumps(data).encode('utf-8')
    print('/quote/create/ Body')
    print(body)
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
    # print("> Response Code: ", response.status_code)
    # print('> Quote/Create Response Data: \n', response.json())
    return response


def construct_rfq_quote_data(rfq_details, min_tick_size,
                             dbt_http_host, bit_http_host,
                             side):
    """
    Create Quote payload.
    """
    client_order_id = f"{paradigm_account_information['desk']}{randint(1, 1000000000)}"
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
            mark, min_buy, min_sell = get_mark_price(venue, leg['instrument'], dbt_http_host, bit_http_host)
            bid, offer = get_bid_and_ask_price(venue, leg['instrument'], mark, min_tick_size)
            # print(f"> mark_price:{mark}, bid_price:{bid}, offer_price:{offer}")
            # print(f"> min_buy:{min_buy}, min_sell:{min_sell}")

            # print('Instrument Name: {}'.format(leg['instrument']))
            # print(f'Min Buy: {min_buy}')
            # print(f'Min Sell: {min_sell}')
            # print(f'Mark Price: {mark}')
            # print(f'Bid: {bid}')
            # print(f'Offer: {offer}')

            if side == 'BUY':
                _price = bid if leg['side'] == 'BUY' else offer
            else:
                _side = 'SELL' if leg['side'] == 'BUY' else 'BUY'
                _price = offer if _side == 'SELL' else bid

            # print(f'Decided Price: {_price}')
            quote_leg['price'] = _price

            # To solve for the issue of a lack of Liquidity on Deribit's testnet
            # for some of the futures products. Once these become more liquid
            # and have bids/asks within the exchange bands, it will be fine to
            # remove the entire section below.
            if venue == 'DBT':
                rfq_id = rfq_details['rfq_id']
                instrument = leg['instrument']
                quote_side = 'BUY' if side == 'BUY' else 'SELL'
                leg_side = 'BUY' if leg['side'] == 'BUY' else 'SELL'
                # print(f'Quote Side: {quote_side}')
                # print(f'Leg Side: {leg_side}')

                if instrument[-1:] not in ['C', 'P']:
                    instrument_type = 'FUTURE'
                else:
                    instrument_type = 'OPTION'

                if quote_side == 'SELL' and leg_side == 'SELL':
                    if bool(_price >= min_sell) is False:
                        quote_leg['price'] = min_sell-5
                        # print(f'Second Decided Price: {min_sell-5}')

                if instrument_type == 'FUTURE':
                    if quote_side == 'SELL' and leg_side == 'BUY':
                        if bool(offer < mark) is False:
                            quote_leg['price'] = mark-50
                            # print(f'Second Decided Price: {mark}')


                if rfq_id not in previous_quotes_dict.keys():
                    previous_quotes_dict[rfq_id] = {}
                if instrument not in previous_quotes_dict[rfq_id].keys():
                    previous_quotes_dict[rfq_id][instrument] = {}
                if side not in previous_quotes_dict[rfq_id][instrument].keys():
                    previous_quotes_dict[rfq_id][instrument][side] = quote_leg['price']

                if 'SELL' in previous_quotes_dict[rfq_id][instrument].keys():
                    if side == 'BUY':
                        print('influenced1')
                        if quote_leg['price'] < previous_quotes_dict[rfq_id][instrument]['SELL']:
                            print('influenced2')
                            quote_leg['price'] = previous_quotes_dict[rfq_id][instrument]['SELL']

                if 'BUY' in previous_quotes_dict[rfq_id][instrument].keys():
                    if side == 'SELL':
                        print('influenced3')
                        if quote_leg['price'] > previous_quotes_dict[rfq_id][instrument]['BUY']:
                            print('influenced4')
                            quote_leg['price'] = previous_quotes_dict[rfq_id][instrument]['BUY']

            # If Mark prices are too low
            if side == 'BUY':
                if quote_leg['price'] <= 0.0002:
                    if venue == "DBT":
                        quote_leg['price'] = round(float(min_buy)+0.0001, 4)
                    elif venue == "BIT":
                        quote_leg['price'] = round(float(min_sell)+0.0001, 4)
            elif side == 'SELL':
                if quote_leg['price'] <= 0.0002:
                    if venue == "DBT":
                        quote_leg['price'] = round(float(min_buy)+0.0001, 4)
                    elif venue == "BIT":
                        quote_leg['price'] = round(float(min_sell)+0.0001, 4)

            # Storing previous prices for two-way quotes, need to add a way to check previous bid/ask
            # and make sure the next quote is equal in value if it's the ask, bid > ask
            # if rfq_details['rfq_id'] not in previous_quotes_dict.keys():
            #     previous_quotes_dict[rfq_details['rfq_id']] = {}
            # elif rfq_details['rfq_id'] in previous_quotes_dict.keys():
            #     pass
            # if leg['instrument'] not in previous_quotes_dict[rfq_details['rfq_id']].keys():
            #     previous_quotes_dict[rfq_details['rfq_id']][leg['instrument']] = [side, quote_leg['price']]
            # elif leg['instrument'] in previous_quotes_dict[rfq_details['rfq_id']].keys():
            #     quote_leg['price'] = quote_leg['price'] if previous_quotes_dict[rfq_details['rfq_id']][leg['instrument']][0] == 'BUY' and _price > previous_quotes_dict[rfq_details['rfq_id']][leg['instrument']][1] else quote_leg['price']

            # print('Quote Price: {}'.format(quote_leg['price']))

        quote_legs.append(quote_leg)

    data = {
        "account": {
            "name": paradigm_account_information['name'][venue]
        },
        "client_order_id": client_order_id,
        "expires_in": randint(60, 120),
        "legs": quote_legs,
        "rfq_id": rfq_details['rfq_id'],
        "side": side
    }
    return data


def get_mark_price(venue, instrument, dbt_http_host, bit_http_host):
    """
    Fetch current mark price for the instrument.
    """
    if venue == 'DBT':
        mark, min_buy, min_sell = get_dbt_mark_price(instrument, dbt_http_host)
        return mark, min_buy, min_sell
    if venue == 'BIT':
        mark, min_buy, min_sell = get_bit_mark_price(instrument, bit_http_host)
        return mark, min_buy, min_sell


def get_dbt_mark_price(instrument, http_host):
    """
    Get ticker details from venue DBT and returns mark price.
    """
    uri = http_host + f"/public/ticker?instrument_name={instrument}"
    response = requests.get(url=uri)
    # result = response.json()['result']
    result = json.loads(response.text)
    result = result['result']
    return result['mark_price'], result['min_price'], result['max_price']


def get_bit_mark_price(instrument, http_host):
    """
    Get ticker details from venue BIT and returns mark price.
    """
    uri = f"{http_host}/tickers?instrument_id={instrument}"
    response = requests.get(url=uri)
    # result = response.json()['data']
    result = json.loads(response.text)
    result = result['data']
    return result['mark_price'], result['max_buy'], result['min_sell']


def get_bid_and_ask_price(venue, instrument, mark_price, min_tick_size):
    """
    Returns bid and ask price calculated based on
    mark price and randomised offset.
    """
    try:
        mark_price = int(mark_price) if float(mark_price).is_integer() else float(mark_price)
    except ValueError:
        mark_price = float(mark_price)

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
    if bid == 0:
        bid = min_tick
    if ask == 0:
        ask = min_tick
    return (bid, ask) if mark_price > 0 else (ask, bid)


def get_min_tick_size(venue, instrument, min_tick_size):
    """ Get minimum quote tick size for the instrument"""
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
            "id": 1,
            "jsonrpc": "2.0",
            "method": "heartbeat"
        }))
        await asyncio.sleep(1)


# Subscription Channel Functions
async def subscribe_rfq_notification(websocket):
    """
    Subscribe to the RFQ Channel to receive rfq notifications.
    """
    print('> Subscribed to RFQ Channel')
    await websocket.send(json.dumps({
        "id": 2,
        "jsonrpc": "2.0",
        "method": "subscribe",
        "params": {
            "channel": "rfq"
        }
    }))


async def subscribe_quote_notifcation(websocket):
    """
    Subscribe to the Quote Channel to receive quote notifications.
    """
    print('> Subscribed to Quote Channel')
    await websocket.send(json.dumps({
        "id": 3,
        "jsonrpc": "2.0",
        "method": "subscribe",
        "params": {
            "channel": "quote"
        }
    }))


async def subscribe_trade_notifcation(websocket):
    """
    Subscribe to the Trade Channel to receive trade notifications.
    """
    print('> Subscribed to Trade Channel')
    await websocket.send(json.dumps({
        "id": 4,
        "jsonrpc": "2.0",
        "method": "subscribe",
        "params": {
            "channel": "trade"
        }
    }))


async def subscribe_tradeconfirmation_notifcation(websocket):
    """
    Subscribe to the Trade Confirmation Channel to receive trade_confirmation notifications.
    """
    print('> Subscribed to Trade Confirmation Channel')
    await websocket.send(json.dumps({
        "id": 5,
        "jsonrpc": "2.0",
        "method": "subscribe",
        "params": {
            "channel": "trade_confirmation"
        }
    }))


if __name__ == "__main__":
    # Arguments for Bash Script
    my_parser = argparse.ArgumentParser()

    my_parser.add_argument('PARADIGM_ACCESS_KEY',
                       metavar='paradigm_access_key',
                       type=str,
                       help='',
                       default='',
                       nargs='?')
    my_parser.add_argument('PARADIGM_SECRET_KEY',
                       metavar='paradigm_secret_key',
                       type=str,
                       help='',
                       default='',
                       nargs='?')
    my_parser.add_argument('PARADIGM_ACCOUNT_NAME_DBT',
                       metavar='paradigm_account_name_dbt',
                       type=str,
                       help='',
                       default='',
                       nargs='?')
    my_parser.add_argument('PARADIGM_ACCOUNT_NAME_BIT',
                       metavar='paradigm_account_name_bit',
                       type=str,
                       help='',
                       default='',
                       nargs='?')
    my_parser.add_argument('PARADIGM_ACCOUNT_NAME_CME',
                       metavar='paradigm_account_name_cme',
                       type=str,
                       help='',
                       default='',
                       nargs='?')
    my_parser.add_argument('PARADIGM_DESK_NAME',
                       metavar='paradigm_desk_name',
                       type=str,
                       help='',
                       default='',
                       nargs='?')
    my_parser.add_argument('PARADIGM_WS_URL',
                       metavar='paradigm_ws_url',
                       type=str,
                       help='',
                       default='',
                       nargs='?')
    my_parser.add_argument('PARADIGM_HTTP_HOST',
                       metavar='paradigm_http_host',
                       type=str,
                       help='',
                       default='',
                       nargs='?')

    # args = my_parser.parse_args()

    # PARADIGM_ACCESS_KEY = args.PARADIGM_ACCESS_KEY
    # PARADIGM_SECRET_KEY = args.PARADIGM_SECRET_KEY
    # PARADIGM_ACCOUNT_NAME_DBT = args.PARADIGM_ACCOUNT_NAME_DBT
    # PARADIGM_ACCOUNT_NAME_BIT = args.PARADIGM_ACCOUNT_NAME_BIT
    # PARADIGM_ACCOUNT_NAME_CME = args.PARADIGM_ACCOUNT_NAME_CME
    # PARADIGM_DESK_NAME = args.PARADIGM_DESK_NAME
    # PARADIGM_WS_URL = args.PARADIGM_WS_URL
    # PARADIGM_HTTP_HOST = args.PARADIGM_HTTP_HOST

    # Local Testing
    # os.environ['PARADIGM_ACCESS_KEY'] = 'vbgCJyYDVXCYodnT80amJPSz'
    # os.environ['PARADIGM_SECRET_KEY'] = 'G78OeQUoOrCcOYI4HW9N+0vJUFlDusR5ZX4DLJIQFrYfd/YZ'
    # os.environ['PARADIGM_ACCOUNT_NAME_DBT'] = "ParadigmTestNinety"
    # os.environ['PARADIGM_ACCOUNT_NAME_BIT'] = "ParadigmTestNinety"
    # os.environ['PARADIGM_ACCOUNT_NAME_CME'] = "ParadigmTestNinety"
    # os.environ['PARADIGM_DESK_NAME'] = "DSK90"

    # os.environ['DBT_HTTP_HOST'] = "https://test.deribit.com/api/v2"
    # os.environ['BIT_HTTP_HOST'] = "https://testapi.bitexch.dev/v1"
    # os.environ['PARADIGM_WS_URL'] = 'wss://ws.api.test.paradigm.co/'
    # os.environ['PARADIGM_HTTP_HOST'] = 'https://api.test.paradigm.co/'

    paradigm_account_information = {
                                    "desk": os.environ['PARADIGM_DESK_NAME'],
                                    "name": {
                                        "DBT": os.environ['PARADIGM_ACCOUNT_NAME_DBT'],
                                        "BIT": os.environ['PARADIGM_ACCOUNT_NAME_BIT'],
                                        "CME": os.environ['PARADIGM_ACCOUNT_NAME_CME']
                                    }}

    # Minimum Tick Size
    MIN_TICK_SIZE = {'DBT': {'BTC': {'OPTION': 0.0001, 'FUTURE': 0.01},
                             'ETH': {'OPTION': 0.0001, 'FUTURE': 0.01}},
                     'BIT': {'BTC': {'OPTION': 0.0001, 'FUTURE': 0.5},
                             'ETH': {'OPTION': 0.0005, 'FUTURE': 0.05}}
                    }

    try:
        print('Paradigm Access Key: {}'.format(os.environ['PARADIGM_ACCESS_KEY']))
        print('Paradigm Sceret Key: {}'.format(os.environ['PARADIGM_SECRET_KEY']))
        print('Paradigm Account Name - DBT: {}'.format(os.environ['PARADIGM_ACCOUNT_NAME_DBT']))
        print('Paradigm Account Name - BIT: {}'.format(os.environ['PARADIGM_ACCOUNT_NAME_BIT']))
        print('Paradigm Account Name - CME: {}'.format(os.environ['PARADIGM_ACCOUNT_NAME_CME']))
        print('Paradigm Desk Name: {}'.format(os.environ['PARADIGM_DESK_NAME']))
        print('HTTP Host - DBT: {}'.format(os.environ['DBT_HTTP_HOST']))
        print('HTTP Host - BIT: {}'.format(os.environ['BIT_HTTP_HOST']))
        print('Paradigm WS URL: {}'.format(os.environ['PARADIGM_WS_URL']))
        print('Paradigm HTTP Host: {}'.format(os.environ['PARADIGM_HTTP_HOST']))

        # Start the client
        asyncio.get_event_loop().run_until_complete(main(access_key=os.environ['PARADIGM_ACCESS_KEY'],
                                                        secret_key=os.environ['PARADIGM_SECRET_KEY'],
                                                        paradigm_account_information =paradigm_account_information,
                                                        dbt_http_host=os.environ['DBT_HTTP_HOST'],
                                                        bit_http_host=os.environ['BIT_HTTP_HOST'],
                                                        paradigm_ws_url=os.environ['PARADIGM_WS_URL'],
                                                        paradigm_http_host=os.environ['PARADIGM_HTTP_HOST'],
                                                        min_tick_size = MIN_TICK_SIZE
                                                        ))

        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print('Local Main Error')
        print('Desk Name: {}'.format(os.environ['PARADIGM_DESK_NAME']))
        print('Paradigm Environment: {}'.format(os.environ['PARADIGM_WS_URL']))
        print('Exception: {}'.format(e))
        print('Traceback Full Logs')
        print(traceback.format_exc())
        sys.exit(1)
