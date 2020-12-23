"""
Paradigm asynchronous websocket application which will automatically
execute the best received quote every 5 seconds or so. You are the Taker.

Usage:
    python3 market_taker.py [ACCESS KEY] [ACCESS SECRET]

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

import asyncio
import base64
import hmac
import json
import os
import random
import requests
import sys
import time
import traceback
import websockets

from urllib.parse import urljoin


try:
    PARADIGM_ACCESS_KEY = sys.argv[1]
    PARADIGM_SECRET_KEY = sys.argv[2]
except IndexError:
    PARADIGM_ACCESS_KEY = None
    PARADIGM_SECRET_KEY = None


async def main(access_key, secret_key, paradigm_account_information,
               paradigm_ws_url, dbt_http_host, bit_http_host,
               paradigm_http_host):
    """
    Primary async function.
    Initially subscribe to all notification channels and create auto quote executor task.
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

        # Used to help manage received RFQs and Quotes.
        rfqs_dict = {}

        # Auto Quote Executor Task
        loop.create_task(auto_quote_execute(rfqs_dict, dbt_http_host, bit_http_host,
                                            access_key, secret_key, paradigm_http_host))

        while True:
            message = await websocket.recv()
            message = json.loads(message)
            # print(f'> {message}')
            if 'params' in message:
                if 'channel' in message['params'].keys():
                    if message['params']['channel'] == 'rfq':
                        # print('> Incoming RFQ')
                        rfq_details = message['params']['data']
                        # print(f'> {rfq_details}')

                        # Add RFQ Id to RFQ dict initially upon RFQ creation
                        if (
                            rfq_details['rfq_id'] not in rfqs_dict.keys()
                            and rfq_details['status'] != 'FILLED'
                        ):
                            rfqs_dict[rfq_details['rfq_id']] = {}

                        # Remove RFQ Id from RFQ dict if an RFQ is canceled
                        if rfq_details['status'] == 'CANCELED':
                            if rfq_details['rfq_id'] in rfqs_dict.keys():
                                rfqs_dict.pop(rfq_details['rfq_id'], None)

                    if message['params']['channel'] == 'quote':
                        # print('> Incoming Quote')
                        quote_details = message['params']['data']
                        # print(f'> {quote_details}')

                        quote_id = quote_details['quote_id']
                        rfq_id = quote_details['rfq_id']

                        # Append quotes to RFQ Dict to help aggregate quotes
                        if quote_id not in rfqs_dict[rfq_id].keys():
                            rfqs_dict[rfq_id][quote_id] = {
                                'desk': quote_details['desk'],
                                'valid_until': quote_details['valid_until'],
                                'status': quote_details['status'],
                            }
                            for leg in range(0, len(quote_details['legs'])):
                                instrument = quote_details['legs'][leg]['instrument']
                                if instrument not in rfqs_dict[rfq_id][quote_id].keys():
                                    rfqs_dict[rfq_id][quote_id][instrument] = {
                                        'side': quote_details['legs'][leg]['side'],
                                        'venue': quote_details['legs'][leg]['venue'],
                                        'bid_price': quote_details['legs'][leg]['bid_price'],
                                        'offer_price': quote_details['legs'][leg]['offer_price'],
                                        'bid_quantity': quote_details['legs'][leg]['bid_quantity'],
                                        'offer_quantity': (
                                            quote_details['legs'][leg]['offer_quantity']
                                        ),
                                    }

                    if message['params']['channel'] == 'trade_confirmation':
                        # print('> Incoming Trade_Confirmation')
                        # trade_confirmation_details = message['params']['data']
                        # print(f'> {trade_confirmation_details}')

                        rfq_id = message['params']['data']['rfq_id']

                        # Remove RFQ Id from RFQ dict upon successful Trade
                        if rfq_id in rfqs_dict.keys():
                            print('Trade Successful')
                            rfqs_dict.pop(rfq_id, None)


# Auto Quote Executor Function
async def auto_quote_execute(rfqs_dict, dbt_http_host, bit_http_host,
                             access_key, secret_key, paradigm_http_host):
    """
    Executes upon best bid/offer randomly after a
    5 second or so delay.
    """
    while True:
        await asyncio.sleep(5)
        rfq_dict_check(rfqs_dict, dbt_http_host, bit_http_host,
                       access_key, secret_key, paradigm_http_host)
        await asyncio.sleep(5)


# RFQ Dict Check Function
def rfq_dict_check(rfqs_dict, dbt_http_host, bit_http_host,
                   access_key, secret_key, paradigm_http_host):
    """
    If rfq_dict contains an rfq with actionable quotes,
    calls the quote_aggregator and quote_execute functions.
    """
    if len(rfqs_dict) != 0:
        for rfq_id in rfqs_dict.keys():
            # If RFQ Id contains at least an actionable quote
            if len(rfqs_dict[rfq_id]) > 0:
                # Returns the /quote/execute/ payload
                best_quote_data = quote_aggregator(rfqs_dict, rfq_id)
                # Executes payload
                quote_execute(best_quote_data, dbt_http_host,
                              bit_http_host, access_key,
                              secret_key, paradigm_http_host)
            # Passes if RFQ Id contains not even a single actionable quote
            elif len(rfqs_dict[rfq_id]) == 0:
                pass


# Quote Aggregator Function
def quote_aggregator(rfqs_dict, rfq_id):
    """
    Aggregates the received quote for the RFQ Id
    from best to worst.
    """
    # Randomize which direction is executed
    direction_list = ['BUY', 'SELL']
    direction_choice = random.choice(direction_list)
    print('Direction Choice: {}'.format(direction_choice))

    _best_quote = {}
    _best_quote[rfq_id] = {}

    # For both directions, store of which quote is the best
    rfq_direction_spread = 0
    opp_rfq_direction_spread = 0

    # Work through rfqs_dict to determine which quote is the bst
    # And to produce the resultant /quote/excute/ payload
    # Evaluates each quote and instrument leg
    for _quote_id in rfqs_dict[rfq_id].keys():
        rfq_direction_spread_list = []
        opp_rfq_direction_spread_list = []
        quote_legs = []
        for instrument in rfqs_dict[rfq_id][_quote_id].keys():
            quote_leg = {}
            if instrument not in ['desk', 'valid_until', 'status']:
                if instrument not in _best_quote[rfq_id].keys():
                    _best_quote[rfq_id][instrument] = {}
                else:
                    pass

                if 'bid_price' not in _best_quote[rfq_id][instrument].keys():
                    _best_quote[rfq_id][instrument]['bid_price'] = 0
                    _best_quote[rfq_id][instrument]['bid_price'] = 0
                    _best_quote[rfq_id][instrument]['bid_quantity'] = 0
                    _best_quote[rfq_id][instrument]['sell_quote_id'] = 0
                    _best_quote[rfq_id][instrument]['sell_desk'] = ''
                else:
                    pass

                if 'offer_price' not in _best_quote[rfq_id][instrument].keys():
                    _best_quote[rfq_id][instrument]['offer_price'] = 0
                    _best_quote[rfq_id][instrument]['offer_price'] = 0
                    _best_quote[rfq_id][instrument]['offer_quantity'] = 0
                    _best_quote[rfq_id][instrument]['buy_quote_id'] = 0
                    _best_quote[rfq_id][instrument]['buy_desk'] = ''
                else:
                    pass

                _side = str(rfqs_dict[rfq_id][_quote_id][instrument]['side'])
                _bid_price = float(
                    rfqs_dict[rfq_id][_quote_id][instrument]['bid_price'].replace(',', ''),
                )
                _bid_quantity = float(
                    rfqs_dict[rfq_id][_quote_id][instrument]['bid_quantity'].replace(',', ''),
                )
                _offer_price = float(
                    rfqs_dict[rfq_id][_quote_id][instrument]['offer_price'].replace(',', ''),
                )
                _offer_quantity = float(
                    rfqs_dict[rfq_id][_quote_id][instrument]['offer_quantity'].replace(',', ''),
                )

                # print('Instrument Name: {}'.format(instrument))
                # print('Direction: {}'.format(_side))
                # print('Bid Price: {}'.format(_bid_price))
                # print('Offer Price: {}'.format(_offer_price))
                # print('Desk: {}'.format(_desk))

                # Price and Quantity values to provide to the payload
                # depending upon the direction_choice
                if direction_choice == 'BUY':
                    if rfqs_dict[rfq_id][_quote_id][instrument]['side'] == 'BUY':
                        quote_leg['price'] = _offer_price
                        quote_leg['quantity'] = _offer_quantity
                    elif rfqs_dict[rfq_id][_quote_id][instrument]['side'] == 'SELL':
                        quote_leg['price'] = _bid_price
                        quote_leg['quantity'] = _bid_quantity

                    quote_leg['side'] = rfqs_dict[rfq_id][_quote_id][instrument]['side']

                elif direction_choice == 'SELL':
                    if rfqs_dict[rfq_id][_quote_id][instrument]['side'] == 'BUY':
                        quote_leg['price'] = _bid_price
                        quote_leg['quantity'] = _bid_quantity
                    elif rfqs_dict[rfq_id][_quote_id][instrument]['side'] == 'SELL':
                        quote_leg['price'] = _offer_price
                        quote_leg['quantity'] = _offer_quantity

                    if rfqs_dict[rfq_id][_quote_id][instrument]['side'] == 'SELL':
                        quote_leg['side'] = 'BUY'
                    elif rfqs_dict[rfq_id][_quote_id][instrument]['side'] == 'BUY':
                        quote_leg['side'] = 'SELL'

                quote_legs.append(quote_leg)

                # Append bid/offer prices to internal spread list for future computation
                if _side == 'BUY':
                    rfq_direction_spread_list.append(_offer_price)
                    opp_rfq_direction_spread_list.append(_bid_price)
                elif _side == 'SELL':
                    rfq_direction_spread_list.append((_bid_price)*-1)
                    opp_rfq_direction_spread_list.append((_offer_price)*-1)

        # Internal Spread variables to compare with previously assessed quotes
        _rfq_direction_spread = 0
        _opp_rfq_direction_spread = 0

        # Determine spread of just assessed quote for BUY direction
        for x in rfq_direction_spread_list:
            _rfq_direction_spread += x

        # Determine spread of just assessed quote for SELL direction
        for x in opp_rfq_direction_spread_list:
            _opp_rfq_direction_spread += x

        # Compare the just assessed quote with the previous best BUY direction quote (less is best)
        if _rfq_direction_spread < rfq_direction_spread or rfq_direction_spread == 0:
            rfq_direction_spread = _rfq_direction_spread

            if direction_choice == 'BUY':
                best_quote_payload = {
                                      'rfq_id': rfq_id,
                                      'legs': quote_legs,
                                      'quote_id': _quote_id
                                    }
        # Compare the just assessed quote with the previous best SELL direction quote (more is best)
        if _opp_rfq_direction_spread > opp_rfq_direction_spread or opp_rfq_direction_spread == 0:
            opp_rfq_direction_spread = _opp_rfq_direction_spread

            if direction_choice == 'SELL':
                best_quote_payload = {
                                      'rfq_id': rfq_id,
                                      'legs': quote_legs,
                                      'quote_id': _quote_id
                                    }
    return best_quote_payload


# Quote Execute Function
def quote_execute(best_quote_data, dbt_http_host,
                  bit_http_host, access_key, secret_key,
                  paradigm_http_host):
    """
    Sends over REST the provided /quote/excute/ payload.
    """
    # print('Payload to Execute')
    # print(best_quote_data)
    method = 'POST'
    path = '/quote/execute/'

    # print('> Quote/Execute Request Data: \n', data)
    body = json.dumps(best_quote_data).encode('utf-8')

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

    response = requests.post(
        urljoin(paradigm_http_host, path), headers=headers, json=best_quote_data,
    )
    # print('> Response Code: ', response.status_code)
    # print('> Quote/Execute Response Data: \n', response.content)
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
        await asyncio.sleep(7)


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
    PARADIGM_ACCOUNT_NAME_DBT = os.getenv(
        'PARADIGM_ACCOUNT_NAME_DBT', 'ParadigmTestOne',
    )
    PARADIGM_ACCOUNT_NAME_BIT = os.getenv(
        'PARADIGM_ACCOUNT_NAME_BIT', 'ParadigmTestOne',
    )
    PARADIGM_ACCOUNT_NAME_CME = os.getenv(
        'PARADIGM_ACCOUNT_NAME_CME', 'ParadigmTestOne',
    )
    PARADIGM_DESK_NAME = os.getenv(
        'PARADIGM_DESK_NAME', 'DSK1',
    )

    DBT_HTTP_HOST = os.getenv(
        'DBT_HTTP_HOST', 'https://test.deribit.com/api/v2',
    )
    BIT_HTTP_HOST = os.getenv(
        'BIT_HTTP_HOST', 'https://testapi.bitexch.dev/v1',
    )
    PARADIGM_WS_URL = os.getenv(
        'PARADIGM_WS_URL', 'wss://ws.api.test.paradigm.co/',
    )
    PARADIGM_HTTP_HOST = os.getenv(
        'PARADIGM_HTTP_HOST', 'https://api.test.paradigm.co',
    )

    paradigm_account_information = {
        'desk': os.environ['PARADIGM_DESK_NAME'],
        'name': {
            'DBT': PARADIGM_ACCOUNT_NAME_DBT,
            'BIT': PARADIGM_ACCOUNT_NAME_BIT,
            'CME': PARADIGM_ACCOUNT_NAME_CME
        }
    }
    try:
        print(f'Paradigm Access Key: {PARADIGM_ACCESS_KEY}')
        print(f'Paradigm Sceret Key: {PARADIGM_SECRET_KEY}')
        print(f'Paradigm Account Name - DBT: {PARADIGM_ACCOUNT_NAME_DBT}')
        print(f'Paradigm Account Name - BIT: {PARADIGM_ACCOUNT_NAME_BIT}')
        print(f'Paradigm Account Name - CME: {PARADIGM_ACCOUNT_NAME_CME}')
        print(f'Paradigm Desk Name: {PARADIGM_DESK_NAME}')
        print(f'HTTP Host - DBT: {DBT_HTTP_HOST}')
        print(f'HTTP Host - BIT: {BIT_HTTP_HOST}')
        print(f'Paradigm WS URL: {PARADIGM_WS_URL}')
        print(f'Paradigm HTTP Host: {PARADIGM_HTTP_HOST}')

        # Start the client that opens a websocket connection and executes RFQs
        asyncio.get_event_loop().run_until_complete(
            main(
                access_key=PARADIGM_ACCESS_KEY,
                secret_key=PARADIGM_SECRET_KEY,
                paradigm_account_information=paradigm_account_information,
                dbt_http_host=DBT_HTTP_HOST,
                bit_http_host=BIT_HTTP_HOST,
                paradigm_ws_url=PARADIGM_WS_URL,
                paradigm_http_host=PARADIGM_HTTP_HOST,
            )
        )

        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print('Local Main Error')
        print(e)
        print(traceback.format_exc())
