"""
Description:
    Paradigm DRFQv2 Automated Market Maker.

    Written December 2022.

    Functionality:
    - Returns orders in response to RFQs
    as the Maker.

    High Level Workflow:
    - Manages tradeable Instruments.
    - Manages RFQs.
    - Manages Orders.
    - Manages Market Data.

Usage:
    python3.9 market-maker.py

Environment Variables:
    LOGGING_LEVEL - Logging Level. 'INFO'.
    ENVIRONMENT - Paradigm Operating Environment. 'TEST', 'NIGHTLY', 'STAGE'
    ACCOUNT_NAME - Paradigm Venue API Key Name.
    ACCESS_KEY - Paradgim Access Key.
    SECRET_KEY - Paradigm Secret Key.
    ORDER_PRICE_WORSE_THAN_MARK_FLAG - If the price should be worse or better than the Mark Price. 'True', 'False'
    ORDER_PRICING_TICK_MULTIPLE - Number of min_tick_sizes to increment from the Mark Price. '0', '1', ...
    ORDER_REFRESH_WINDOW_LOWER_BOUNDARY - Lower bound of order refresh window in seconds.
    ORDER_REFRESH_WINDOW_UPPER_BOUNDARY - Upper bound of order refresh window in seconds.

Requirements:
    pip3 install websockets
    pip3 install aiohttp
"""

# built ins
import asyncio
import os
import logging

# project
from interface_clients.websockets import ParadigmWebSocketClient
from interface_clients.rest import ParadigmRESTClient
from helpers.managers import ManagedInstruments, MakerManagedRFQs, \
     ManagedMMP
from helpers.order_manager import MakerOrderManager
from helpers.processors import ParadigmWSMessageProcessor
from helpers.constants import OrderState, RFQState


class main:
    """
    Primary service management class.
    """
    def __init__(
        self,
        ws_url: str,
        http_url: str,
        account_name: str,
        access_key: str,
        secret_key: str,
        order_price_worse_than_mark_flag: str,
        order_pricing_tick_multiple: str,
        order_refresh_window_lower_boundary: str,
        order_refresh_window_upper_boundary: str
            ) -> None:
        self.ws_url: str = ws_url
        self.http_url: str = http_url
        self.account_name: str = account_name
        self.access_key: str = access_key
        self.secret_key: str = secret_key
        self.order_price_worse_than_mark_flag: bool = bool(
            order_price_worse_than_mark_flag
            )
        self.order_pricing_tick_multiple: int = int(
            order_pricing_tick_multiple
            )
        self.order_refresh_window_lower_boundary: float = float(
            order_refresh_window_lower_boundary
            )
        self.order_refresh_window_upper_boundary: float = float(
            order_refresh_window_upper_boundary
            )

        # Instance Variables
        self.ws_msg_queue: asyncio.Queue = asyncio.Queue()

        # Instantiate Market Maker Coroutine
        asyncio.get_event_loop().run_until_complete(
            self.market_maker()
            )

    async def market_maker(self):
        """
        Primary coroutine to coordinate and manage dependencies
        to make markets.
        """
        # Instantiate RESToverHTTP Client
        self.rest_client: ParadigmRESTClient = ParadigmRESTClient(
            connection_url=self.http_url,
            access_key=self.access_key,
            secret_key=self.secret_key
            )

        # Log the number of OPEN Orders
        response = await self.rest_client.get_orders(
            state=OrderState.OPEN
            )
        no_orders: int = len(response)
        logging.info(f'No OPEN Orders: {no_orders}')

        # Log the number of OPEN RFQs
        response = await self.rest_client.get_rfqs(
            state=RFQState.OPEN
            )
        no_rfqs: int = len(response)
        logging.info(f'No OPEN RFQs: {no_rfqs}')

        # Instantiate WebSocket Client
        self.ws_client: ParadigmWebSocketClient = ParadigmWebSocketClient(
            connection_url=self.ws_url,
            access_key=self.access_key,
            exgest_queue=self.ws_msg_queue,
            channels_to_subscribe_on_start=[
                'rfqs',
                'orders',
                'market_maker_protection'
                ]
            )

        # Instantiate Instrument Management Class
        self.managed_instruments: ManagedInstruments = ManagedInstruments(
            rest_client=self.rest_client
            )

        # Instantiate RFQ Management Class
        self.managed_rfqs: MakerManagedRFQs = MakerManagedRFQs(
            rest_client=self.rest_client,
            ws_client=self.ws_client,
            managed_instruments=self.managed_instruments
            )

        # Instantiate MMP Manager
        self.managed_mmp: ManagedMMP = ManagedMMP(
            rest_client=self.rest_client
            )

        # Instantiate WebSocket Message Processor
        self.ws_message_processor: ParadigmWSMessageProcessor = ParadigmWSMessageProcessor(
            message_queue=self.ws_msg_queue,
            managed_rfqs=self.managed_rfqs,
            managed_mmp=self.managed_mmp
            )

        # Instantiate Order Manager
        self.order_manager: MakerOrderManager = MakerOrderManager(
            account_name=self.account_name,
            rest_client=self.rest_client,
            order_price_worse_than_mark_flag=self.order_price_worse_than_mark_flag,
            order_pricing_tick_multiple=self.order_pricing_tick_multiple,
            order_refresh_window_lower_boundary=self.order_refresh_window_lower_boundary,
            order_refresh_window_upper_boundary=self.order_refresh_window_upper_boundary,
            managed_rfqs=self.managed_rfqs,
            managed_mmp=self.managed_mmp
            )

        # Test Create RFQ
        # asyncio.get_event_loop().create_task(
        #     self.test_create_rfq()
        #     )

        while True:
            await asyncio.sleep(600)

    async def test_create_rfq(self) -> None:
        while not self.ws_client.connection_authentication:
            await asyncio.sleep(0)
        client: ParadigmRESTClient = ParadigmRESTClient(
            connection_url=self.http_url,
            access_key='Z9gBdD05yiHLotRCxrSeFTfC',
            secret_key='9qgG7DU0XNaqF9n5Q35iQtL5Bv7JFNUffagT7/qC9jlH0exj'
            )

        while True:
            status_code, response = await client.post_rfq(
                payload={
                        "venue": "DBT",
                        "quantity": "25",
                        "is_taker_anonymous": True,
                        "counterparties": ["DSK94"],
                        "legs": [
                            {
                            "instrument_id": "182243",
                            "ratio": "1",
                            "side": "SELL"
                            },
                            {
                            "instrument_id": "182244",
                            "ratio": "1",
                            "side": "BUY"
                            }
                        ]
                        }
                )
            rfq_id: str = response['id']
            logging.info(f'Created RFQ ID : {rfq_id}')
            await asyncio.sleep(10)


if __name__ == "__main__":
    # Paradigm Operating Environment
    environment = os.getenv('ENVIRONMENT', 'TESTNET')
    # Paradigm Connection URLs
    ws_url: str = f'wss://ws.api.{environment.lower()}.paradigm.trade/v2/drfq'
    http_url: str = f'https://api.{environment.lower()}.paradigm.trade'

    # Logging
    logging.basicConfig(
        level=os.environ['LOGGING_LEVEL'],
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Instantiate Service
    main(
        ws_url=ws_url,
        http_url=http_url,
        account_name=os.environ['MAKER_ACCOUNT_NAME'],
        access_key=os.environ['MAKER_ACCESS_KEY'],
        secret_key=os.environ['MAKER_SECRET_KEY'],
        order_price_worse_than_mark_flag=os.environ['ORDER_PRICE_WORSE_THAN_MARK_FLAG'],
        order_pricing_tick_multiple=os.environ['ORDER_PRICING_TICK_MULTIPLE'],
        order_refresh_window_lower_boundary=os.environ['ORDER_REFRESH_WINDOW_LOWER_BOUNDARY'],
        order_refresh_window_upper_boundary=os.environ['ORDER_REFRESH_WINDOW_UPPER_BOUNDARY']
        )
