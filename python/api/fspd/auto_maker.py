"""
Description:
    Paradigm FSPD Automated Market Maker.

    Functionality:
    - Provides the number of quotes per Strategy,
    per side as per specified in the environment
    variable.

    Design Notes:
    - Uses entirely Paradigm's API for everything
    (data + actions).

    High Level Workflow:
    - Pull existing Strategies and subscribes to requisite
    WebSocket Channels.
    - Creates Order Payloads + Submits Orders.
    - Refreshes Orders.

Usage:
    python3 market-maker.py

Environment Variables:
    PARADIGM_ENVIRONMENT - Paradigm Operating Environment.
    LOGGING_LEVEL - Logging Level. 'INFO'.
    PARADIGM_MAKER_ACCOUNT_NAME - Paradigm Venue API Key Name.
    PARADIGM_MAKER_ACCESS_KEY - Paradgim Maker Access Key.
    PARADIGM_MAKER_SECRET_KEY - Paradigm Maker Secret Key.

    ORDER_NUMBER_PER_SIDE - Number of Orders to maintain per side of
                            each Strategy.
    QUOTE_QUANTITY_LOWER_BOUNDARY - Lower Bound No. ticks from Block
                                    Size Minimum.
    QUOTE_QUANTITY_HIGHER_BOUNDARY - Upper Bound No. ticks from Block
                                     Size Minimum.
    QUOTE_PRICE_LOWER_BOUNDARY - Lower Bound No. ticks from Minimum Tick
                                 Size.
    QUOTE_PRICE_HIGHER_BOUNDARY - Upper Bound No. ticks from Minimum
                                  Tick Size.
Requirements:
    pip3 install websockets
    pip3 install aiohttp
"""

import asyncio
import base64
import hmac
import json
import logging
import math
import os
import signal
import time
from random import randint, shuffle
from typing import Dict, List, Tuple

import aiohttp
import websockets

# AMM order state:
managed_strategies = {}
strategy_order_payloads = {}

# transmission control
rate_limit_dict = {}


def shutdown():
    asyncio.get_event_loop().run_until_complete(cancel_all_orders())


async def main() -> None:
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, shutdown)
    loop.create_task(rate_limit_refiller())
    loop.create_task(manage_websocket_messages())
    loop.create_task(order_manager())


# Coroutines
async def manage_websocket_messages() -> None:
    """
    Manages incoming WS messages as well as
    on initialization pulls all available
    Strategies and stores them locally.
    """
    global managed_strategies
    global strategy_order_payloads

    # try:
    # Cancel all Desk Orders
    await cancel_all_orders()
    await asyncio.sleep(5)
    # Pull all available Strategies
    strategies: Dict = await get_strategies()
    # Ingest available Strategies
    await ingest_strategies(strategies=strategies)

    loop = asyncio.get_event_loop()

    # WebSocket Subscriptions
    async with websockets.connect(
        f'{paradigm_ws_url}?api-key={credentials["access_key"]}'
    ) as websocket:
        # Start the Heartbeat Task
        loop.create_task(send_heartbeat(websocket=websocket))
        # Subscribe to the `strategy_state.{venue}.{kind}`
        # WS Channel
        await subscribe_strategy_state_notifications(websocket=websocket)
        # Subscribe to the `orders.{venue}.{kind}.{strategy_id}`
        # WS Channel
        await subscribe_orders_notifications(websocket=websocket)
        # Subscribe to the `venue_bbo.{strategy_id}` WS Channel
        await subscribe_venue_bbo_notification(websocket=websocket)

        message_channel: str = None

        while True:
            # Receive WebSocket messages
            message = await websocket.recv()
            message = json.loads(message)

            if 'id' in list(message):
                message_id: int = message['id']
                if message_id == 1:
                    # Heartbeat Response
                    continue
                else:
                    channel_subscribed: str = message['result']['channel']
                    logging.info(
                        f'Successfully Subscribed to WebSocket Channel: {channel_subscribed}'
                    )
            else:
                message_channel = message['params']['channel']

            if message_channel == 'strategy_state.ALL.ALL':
                state: str = message['params']['data']['state']
                strategy_id: str = message['params']['data']['id']

                # Ingest New Strategies
                if state == 'ACTIVE':
                    # Pull strategies endpoint for all the deets
                    strategies: Dict = await get_strategies(strategy_id=strategy_id)
                    # Ingest New Strategies
                    await ingest_strategies(
                        strategies=strategies,
                    )
                else:
                    # Exgest Settled/Expired Strategies
                    await exgest_strategies(
                        strategy_id=strategy_id,
                    )

            elif message_channel == 'orders.ALL.ALL.ALL':
                order_label: str = message['params']['data']['label']
                order_id: str = message['params']['data']['id']
                state: str = message['params']['data']['state']
                logging.info(f"{order_id=} {order_label=} {state=}")

            elif message_channel == 'venue_bbo.ALL':
                strategy_id: str = message['params']['data']['id']
                min_price: str = message['params']['data']['min_price']
                max_price: str = message['params']['data']['max_price']
                mark_price: str = message['params']['data']['mark_price']
                best_bid_price: str = message['params']['data']['best_bid_price']
                best_ask_price: str = message['params']['data']['best_ask_price']

                if strategy_id in managed_strategies:
                    managed_strategies[strategy_id]['min_price'] = min_price
                    managed_strategies[strategy_id]['max_price'] = max_price
                    managed_strategies[strategy_id]['mark_price'] = mark_price
                    managed_strategies[strategy_id]['best_bid_price'] = best_bid_price
                    managed_strategies[strategy_id]['best_ask_price'] = best_ask_price
                else:
                    logging.info("websocket venue_bbo strategy_id not in managed_strategies")

            await asyncio.sleep(0)


async def ingest_strategies(
    strategies: Dict,
) -> None:
    """
    Ingests the response of the get_strategies()
    coroutine.
    """
    global managed_strategies
    global strategy_order_payloads

    no_strategies: int = len(strategies)
    order_number_per_side = order_configuration['order_number_per_side']

    logging.info(
        f"Ingesting {no_strategies=} strategies, "
        f"starting with {len(managed_strategies)=}, "
        f"creating {order_number_per_side} orders per side."
    )
    for strategy in range(no_strategies):
        strategy_id: str = strategies[strategy]['id']
        venue: str = strategies[strategy]['venue']
        min_order_size: float = strategies[strategy]['min_order_size']
        min_tick_size: float = float(strategies[strategy]['min_tick_size'])
        min_block_size: float = strategies[strategy]['min_block_size']

        managed_strategies[strategy_id] = {
            'venue': venue,
            'min_order_size': min_order_size,
            'min_tick_size': min_tick_size,
            'min_block_size': min_block_size,
            'min_price': None,
            'max_price': None,
            'mark_price': None,
            'best_bid_price': None,
            'best_ask_price': None,
        }

        # Creating Order Payloads
        for order in range(order_number_per_side):
            for side in ['BUY', 'SELL']:
                label: str = f'{strategy_id}-{side}-{order}'
                if label not in list(strategy_order_payloads):
                    strategy_order_payloads[label] = {
                        'side': side,
                        'strategy_id': strategy_id,
                        'price': None,
                        'amount': None,
                        'type': 'LIMIT',
                        'label': label,
                        'time_in_force': 'GOOD_TILL_CANCELED',
                        'account_name': credentials['account_name'],
                        'order_id': None,
                        'order_number': order,  # Save in order to be able to recreate the label.
                        'replacing_order': False,
                    }


async def exgest_strategies(strategy_id: str) -> None:
    """
    Exgests Strategies and Order Payloads
    from local stores.
    """
    global managed_strategies
    global strategy_order_payloads

    order_number_per_side = order_configuration['order_number_per_side']

    # Remove from the managed_strategies dict
    managed_strategies.pop(strategy_id)

    # Remove Orders from strategy_order_payloads dict
    for order in range(order_number_per_side):
        for side in ['BUY', 'SELL']:
            label: str = f'{strategy_id}-{side}-{order}'
            if label in list(strategy_order_payloads):
                strategy_order_payloads.pop(label)


async def rate_limiter(venue: str, rate_limit_increment: int) -> int:
    """
    Function ensures rate limit is respected.

    Paradigm's default rate limit is
    200 requests per second per account.
    """
    global rate_limit_dict

    run_flag: int = 0

    if venue not in list(rate_limit_dict):
        return run_flag

    if 'remaining_amount' not in list(rate_limit_dict[venue]):
        return run_flag

    if rate_limit_dict[venue]['remaining_amount'] >= 1:
        rate_limit_dict[venue]['remaining_amount'] -= rate_limit_increment
        run_flag = 1
    return run_flag


async def rate_limit_refiller() -> None:
    """
    This coroutine refills the rate limit
    buckets per the venue's Rate Limit convention.
    """
    global rate_limit_dict

    venue_rate_limits: Dict = {'PDGM': 200}

    remaining_refresh_boundary: float = time.time() + 1

    for venue in list(venue_rate_limits):
        if venue not in list(rate_limit_dict):
            rate_limit_dict[venue] = {}
        if 'remaining_amount' not in list(rate_limit_dict[venue]):
            rate_limit_dict[venue]['remaining_amount'] = venue_rate_limits[venue]

    while True:
        while time.time() > remaining_refresh_boundary:
            remaining_refresh_boundary = time.time() + 1

            for venue in list(venue_rate_limits):
                rate_limit_dict[venue]['remaining_amount'] = venue_rate_limits[venue]

        await asyncio.sleep(1)


def order_creator() -> Tuple[List[str], List[str]]:
    """
    Creates Order Payloads
    """
    global strategy_order_payloads

    order_number_per_side = order_configuration['order_number_per_side']
    quote_quantity_lower_boundary = order_configuration['quote_quantity_lower_boundary']
    quote_quantity_higher_boundary = order_configuration['quote_quantity_higher_boundary']
    quote_price_tick_diff_lower_boundary = order_configuration[
        'quote_price_tick_diff_lower_boundary'
    ]
    quote_price_tick_diff_higher_boundary = order_configuration[
        'quote_price_tick_diff_higher_boundary'
    ]

    orders_to_submit = []
    orders_to_replace = []

    for strategy in list(managed_strategies):
        for side in ['BUY', 'SELL']:
            for order in range(order_number_per_side):
                label: str = f'{strategy}-{side}-{order}'

                if strategy_order_payloads[label]['replacing_order']:
                    continue

                # Update Amount
                min_order_size: int = managed_strategies[strategy]['min_order_size']
                min_block_size: int = managed_strategies[strategy]['min_block_size']

                random_multiple: int = randint(
                    quote_quantity_lower_boundary, quote_quantity_higher_boundary
                )

                base_amount: int = max(min_block_size, min_order_size)
                total_amount: int = base_amount + (random_multiple * min_order_size)

                strategy_order_payloads[label]['amount'] = total_amount

                min_tick_size: int = managed_strategies[strategy]['min_tick_size']

                if managed_strategies[strategy]['min_price'] is None:
                    continue
                mark_price: float = float(managed_strategies[strategy]['mark_price'])

                # Price just off the Mark Price if both price variables
                # are set to 0
                price_at_mark_flag: int = (
                    1
                    if quote_price_tick_diff_lower_boundary == 0
                    and quote_price_tick_diff_higher_boundary == 0
                    else 0
                )

                random_price_multiple: int = randint(
                    quote_price_tick_diff_lower_boundary, quote_price_tick_diff_higher_boundary
                )

                if price_at_mark_flag == 0:
                    if side == 'BUY':
                        price: float = mark_price - (
                            random_price_multiple
                            * (order + 2 * min_tick_size)  # 5000-75000 * (0-5  + 2 * $.01)
                        )
                    elif side == 'SELL':
                        price: float = mark_price + (
                            random_price_multiple * (order + 2 * min_tick_size)
                        )
                else:
                    if side == 'BUY':
                        price: float = mark_price - (
                            random_price_multiple * (order * min_tick_size)
                        )
                    elif side == 'SELL':
                        price: float = mark_price + (
                            random_price_multiple * (order * min_tick_size)
                        )

                # Ensure Price is within the min_tick_size increments
                price: str = str(round_nearest(price, min_tick_size))

                strategy_order_payloads[label]['price'] = price

                if strategy_order_payloads[label]['order_id']:
                    orders_to_replace.append(label)
                    strategy_order_payloads[label]['replacing_order'] = True
                else:
                    orders_to_submit.append(label)

    return orders_to_submit, orders_to_replace


async def order_manager_one_iteration():
    global strategy_order_payloads

    orders_to_submit, orders_to_replace = order_creator()

    logging.info(
        f'Submitting {len(orders_to_submit)} new orders and '
        f'replacing {len(orders_to_replace)} orders. Based off of {len(strategy_order_payloads)=}.'
    )

    loop = asyncio.get_event_loop()
    for label in orders_to_submit:
        loop.create_task(
            post_orders(
                payload=strategy_order_payloads[label],
            )
        )

    for label in orders_to_replace:
        loop.create_task(
            post_orders_orderid_replace(
                payload=strategy_order_payloads[label],
            )
        )


async def order_manager() -> None:
    loop = asyncio.get_event_loop()
    quote_refresh = order_configuration['quote_refresh']
    while True:
        loop.create_task(order_manager_one_iteration())
        await asyncio.sleep(quote_refresh)


def round_nearest(x, a):
    """
    Used to round random prices to the
    correct min_tick_size of the Strategy.
    """
    return round(round(x / a) * a, -int(math.floor(math.log10(a))))


def rate_limit_decorator(f):
    async def wrapper(*args, **kwargs):
        run_flag: int = 0
        while run_flag == 0:
            run_flag = await rate_limiter(venue='PDGM', rate_limit_increment=1)
            await asyncio.sleep(0)
        return await f(*args, **kwargs)

    return wrapper


# RESToverHTTP Interface
def sign_request(
    paradigm_maker_secret_key: str, method: str, path: str, body: str
) -> Tuple[bytes, bytes]:
    """
    Creates the required signature neccessary
    as apart of all RESToverHTTP requests with Paradigm.
    """
    _secret_key: bytes = paradigm_maker_secret_key.encode('utf-8')
    _method: bytes = method.encode('utf-8')
    _path: bytes = path.encode('utf-8')
    _body: bytes = body.encode('utf-8')
    signing_key: bytes = base64.b64decode(_secret_key)
    timestamp: bytes = str(int(time.time() * 1000)).encode('utf-8')
    message: bytes = b'\n'.join([timestamp, _method.upper(), _path, _body])
    digest: hmac.digest = hmac.digest(signing_key, message, 'sha256')
    signature: bytes = base64.b64encode(digest)

    return timestamp, signature


def create_rest_headers(
    paradigm_maker_access_key: str,
    paradigm_maker_secret_key: str,
    method: str,
    path: str,
    body: str,
) -> Dict:
    """
    Creates the required headers to authenticate
    Paradigm RESToverHTTP requests.
    """
    timestamp, signature = sign_request(
        paradigm_maker_secret_key=paradigm_maker_secret_key, method=method, path=path, body=body
    )

    return {
        'Paradigm-API-Timestamp': timestamp.decode('utf-8'),
        'Paradigm-API-Signature': signature.decode('utf-8'),
        'Authorization': f'Bearer {paradigm_maker_access_key}',
    }


@rate_limit_decorator
async def get_strategies(strategy_id: str = None) -> Dict:
    """
    Paradigm RESToverHTTP endpoint.
    [GET] /strategies
    """
    method: str = 'GET'
    path: str = '/v1/fs/strategies?page_size=100'
    payload: str = ''

    if strategy_id is not None:
        path += f'&id={strategy_id}'

    headers: Dict = create_rest_headers(
        paradigm_maker_access_key=credentials['access_key'],
        paradigm_maker_secret_key=credentials['secret_key'],
        method=method,
        path=path,
        body=payload,
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(paradigm_http_url + path, headers=headers) as raw_response:
            raw_response: aiohttp.ClientResponse
            status_code: int = raw_response.status
            response: Dict = await raw_response.json()
            if status_code != 200:
                message: str = 'Unable to [GET] /strategies'
                if strategy_id is not None:
                    message += f'?id={strategy_id}'
                logging.error(message)
                logging.error(f'Status Code: {status_code}')
                logging.error(f'Response Text: {response}')
            response = response['results']
    return response


@rate_limit_decorator
async def cancel_all_orders() -> None:
    """
    Paradigm RESToverHTTP endpoint.
    [DELETE] /orders
    """
    method: str = 'DELETE'
    path: str = '/v1/fs/orders'
    payload: str = ''

    headers: Dict = create_rest_headers(
        paradigm_maker_access_key=credentials['access_key'],
        paradigm_maker_secret_key=credentials['secret_key'],
        method=method,
        path=path,
        body=payload,
    )

    async with aiohttp.ClientSession() as session:
        async with session.delete(paradigm_http_url + path, headers=headers) as response:
            status_code: int = response.status
            if status_code != 204:
                logging.error('Unable to [DELETE] /orders')
                logging.error(f'Status Code: {status_code}')
            else:
                logging.info('Successsfully canceled all Orders.')


@rate_limit_decorator
async def post_orders(payload: Dict) -> bool:
    """
    Paradigm RESToverHTTP endpoint.
    [POST] /orders
    """
    method: str = 'POST'
    path: str = '/v1/fs/orders'

    _payload: Dict = payload.copy()
    _payload.pop('order_id', None)
    payload_body: str = json.dumps(_payload)

    headers: Dict = create_rest_headers(
        paradigm_maker_access_key=credentials['access_key'],
        paradigm_maker_secret_key=credentials['secret_key'],
        method=method,
        path=path,
        body=payload_body,
    )

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                paradigm_http_url + path, headers=headers, json=_payload
            ) as raw_response:
                raw_response: aiohttp.ClientResponse
                status_code: int = raw_response.status
                response: Dict = await raw_response.json(content_type=None)
                if status_code == 201:
                    order_id = response['id']
                    payload['order_id'] = order_id
                    return True
                else:
                    return False

        except aiohttp.ClientConnectorError as e:
            logging.error(f'[POST] /orders ClientConnectorError: {e}')
            return False


@rate_limit_decorator
async def post_orders_orderid_replace(payload: Dict) -> None:
    """
    Paradigm RESToverHTTP endpoint.
    [POST] /orders/{order_id}/replace
    """

    order_id = payload['order_id']
    method: str = 'POST'
    path: str = f'/v1/fs/orders/{order_id}/replace'

    _payload: Dict = dict(payload)
    label: str = f"{_payload['strategy_id']}-{_payload['side']}-{_payload['order_number']}"
    for key in [
        'side',
        'strategy_id',
        'replacing_order',
        'order_number',
    ]:
        _payload.pop(key)

    _payload['order_id'] = order_id
    __payload: str = json.dumps(_payload)

    headers: Dict = create_rest_headers(
        paradigm_maker_access_key=credentials['access_key'],
        paradigm_maker_secret_key=credentials['secret_key'],
        method=method,
        path=path,
        body=__payload,
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                paradigm_http_url + path, headers=headers, json=_payload
            ) as raw_response:
                raw_response: aiohttp.ClientResponse
                status_code: int = raw_response.status
                response: Dict = await raw_response.json(content_type=None)
                if status_code == 201:
                    order_id = response['id']
                    payload['order_id'] = order_id
                elif status_code == 403 and response and response.get('code') == 4003:
                    # a Taker may have taken the order.
                    pass
                else:
                    logging.error('POST not accepted.')

    except aiohttp.ClientConnectorError as e:
        logging.error(f'[POST] /orders ClientConnectorError: {e}')
    finally:
        strategy_order_payloads[label]['replacing_order'] = False


# JSON-RPCoverWebsocket Interface
async def send_heartbeat(websocket: websockets.WebSocketClientProtocol) -> None:
    """
    Sends a Heartbeat to keep the Paradigm WebSocket connection alive.
    """
    while True:
        logging.debug("Sending Heartbeat")
        await websocket.send(json.dumps({"id": 1, "jsonrpc": "2.0", "method": "heartbeat"}))
        await asyncio.sleep(5)


async def subscribe_strategy_state_notifications(
    websocket: websockets.WebSocketClientProtocol,
) -> None:
    """
    Subscribe to the `strategy_stage.{venue}.{kind}` WS Channel.
    """
    await websocket.send(
        json.dumps(
            {
                "id": 2,
                "jsonrpc": "2.0",
                "method": "subscribe",
                "params": {"channel": "strategy_state.ALL.ALL"},
            }
        )
    )


async def subscribe_orders_notifications(websocket: websockets.WebSocketClientProtocol) -> None:
    """
    Subscribe to the `orders.{venue}.{kind}.{strategy_id}` WS Channel.
    """
    await websocket.send(
        json.dumps(
            {
                "id": 3,
                "jsonrpc": "2.0",
                "method": "subscribe",
                "params": {"channel": "orders.ALL.ALL.ALL"},
            }
        )
    )


async def subscribe_venue_bbo_notification(websocket: websockets.WebSocketClientProtocol) -> None:
    """
    Subscribe to the `venue_bbo.{strategy_id}` WS Channel.
    """
    await websocket.send(
        json.dumps(
            {
                "id": 4,
                "jsonrpc": "2.0",
                "method": "subscribe",
                "params": {"channel": "venue_bbo.ALL"},
            }
        )
    )


if __name__ == "__main__":

    # Paradigm Connection URLs
    paradigm_environment = os.getenv('PARADIGM_ENVIRONMENT', 'TEST')
    if paradigm_environment.lower() == 'prod':
        paradigm_environment = 'chat'

    paradigm_ws_url: str = f'wss://ws.api.fs.{paradigm_environment.lower()}.paradigm.co/v1/fs'
    paradigm_http_url: str = f'https://api.fs.{paradigm_environment.lower()}.paradigm.co'

    # Logging
    log_name = "debug_amm.log"
    logging.basicConfig(
        level=os.environ.get('LOGGING_LEVEL', 'INFO'),
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.FileHandler(log_name, 'w', 'utf-8'), logging.StreamHandler()],
    )

    credentials = {
        'account_name': os.environ['PARADIGM_MAKER_ACCOUNT_NAME'],
        'access_key': os.environ['PARADIGM_MAKER_ACCESS_KEY'],
        'secret_key': os.environ['PARADIGM_MAKER_SECRET_KEY'],
    }

    order_configuration = {
        'order_number_per_side': int(os.environ.get('ORDER_NUMBER_PER_SIDE', '5')),
        'quote_quantity_lower_boundary': int(os.environ.get('QUOTE_QUANTITY_LOWER_BOUNDARY', '10')),
        'quote_quantity_higher_boundary': int(os.environ.get('QUOTE_QUANTITY_HIGHER_BOUNDARY', '100')),
        'quote_price_tick_diff_lower_boundary': int(os.environ.get('QUOTE_PRICE_TICK_DIFF_LOWER_BOUNDARY', '100')),
        'quote_price_tick_diff_higher_boundary': int(os.environ.get('QUOTE_PRICE_TICK_DIFF_HIGHER_BOUNDARY', '1000')),
        'quote_refresh': 5,
    }

    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_forever()
