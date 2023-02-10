"""
Description:
    Paradigm DRFQv2 Automated Market Taker.

    Written December 2022.

    Functionality:
    - Creates RFQs.
    - Executes upon the RFQ.

    High Level Workflow:
    - Manages tradeable Instruments.
    - Manages RFQs.
    - Manages RFQ Orders.

Usage:
    python3.9 market-maker.py

Environment Variables:
    LOGGING_LEVEL - Logging Level. 'INFO'.
    ENVIRONMENT - Paradigm Operating Environment. 'TEST', 'NIGHTLY', 'STAGE'
    ACCOUNT_NAME - Paradigm Venue API Key Name.
    ACCESS_KEY - Paradgim Access Key.
    SECRET_KEY - Paradigm Secret Key.

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
from helpers.managers import ManagedInstruments, TakerManagedRFQs
from helpers.rfq_creator import RFQCreator
from helpers.order_manager import TakerOrderManager
from helpers.processors import ParadigmWSMessageProcessor
from helpers.constants import RFQState


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
        secret_key: str
            ) -> None:
        self.ws_url: str = ws_url
        self.http_url: str = http_url
        self.account_name: str = account_name
        self.access_key: str = access_key
        self.secret_key: str = secret_key

        # Instance Variables
        self.ws_msg_queue: asyncio.Queue = asyncio.Queue()

        # Instantiate Market Maker Coroutine
        asyncio.get_event_loop().run_until_complete(
            self.market_taker()
            )

    async def market_taker(self):
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
                'rfq_orders'
                ]
            )

        # Instantiate Instrument Management Class
        self.managed_instruments: ManagedInstruments = ManagedInstruments(
            rest_client=self.rest_client
            )

        # Instantiate RFQ Management Class
        self.managed_rfqs: TakerManagedRFQs = TakerManagedRFQs(
            rest_client=self.rest_client,
            ws_client=self.ws_client,
            managed_instruments=self.managed_instruments
            )

        # Instantiate RFQ Creator Class
        self.rfq_creator: RFQCreator = RFQCreator(
            account_name=self.account_name,
            rest_client=self.rest_client,
            managed_instruments=self.managed_instruments
            )

        # Instantiate WebSocket Message Processor
        self.ws_message_processor: ParadigmWSMessageProcessor = ParadigmWSMessageProcessor(
            message_queue=self.ws_msg_queue,
            managed_rfqs=self.managed_rfqs
            )

        # Instantiate Order Manager
        self.order_manager: TakerOrderManager = TakerOrderManager(
            account_name=self.account_name,
            rest_client=self.rest_client,
            managed_rfqs=self.managed_rfqs
            )

        while True:
            await asyncio.sleep(600)


if __name__ == "__main__":
    # Paradigm Operating Environment
    environment = os.getenv('ENVIRONMENT', 'NIGHTLY')
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
        account_name=os.environ['TAKER_ACCOUNT_NAME'],
        access_key=os.environ['TAKER_ACCESS_KEY'],
        secret_key=os.environ['TAKER_SECRET_KEY']
        )
