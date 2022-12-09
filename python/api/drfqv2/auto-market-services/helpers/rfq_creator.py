# built ins
import asyncio
import logging
from typing import Dict, List
from random import randint, choice

# project
from helpers.managers import ManagedInstruments
from interface_clients.rest import ParadigmRESTClient
from helpers.constants import OrderDirection
from helpers.resources import Instrument


class RFQCreator:
    """
    Primary class to manage the creation of RFQs.
    """
    def __init__(
        self,
        rest_client: ParadigmRESTClient,
        managed_instruments: ManagedInstruments
            ) -> None:
        self.rest_client: ParadigmRESTClient = rest_client
        self.managed_instruments: ManagedInstruments = managed_instruments

        # Instantiate Periodic RFQ Create
        asyncio.get_event_loop().create_task(
            self.periodic_rfq_create()
            )

    async def determine_initial_instruments_request_concluded(self) -> None:
        """
        Waits until the initial [GET] `/instruments` request is finished.
        """
        while len(list(self.managed_instruments.instruments)) < 50:
            await asyncio.sleep(0)

    async def determine_supported_venues(self) -> List[str]:
        """
        Iterates through the managed Instruments to determine
        the supported venues.
        """
        return ['DBT']
        venues: List[str] = []
        for instrument_id, instrument in self.managed_instruments.instruments.items():
            if instrument.venue not in venues:
                venues.append(instrument.venue)
        return venues

    async def create_random_side(self) -> str:
        """
        Creates and returns random side.
        """
        side: OrderDirection = choice(list(OrderDirection))
        return side.name

    async def choose_random_instrument_kind(self) -> str:
        """
        Returns random instrument kind.
        """
        return 'OPTION'

    async def choose_random_base_currency(self) -> str:
        return choice(['BTC', 'ETH'])

    async def choose_random_instrument(
        self,
        venue: str,
        kind: str,
        base_currency: str
            ) -> Instrument:
        """
        Returns a random Instrument id.
        """
        while True:
            instrument_id: str = choice(list(self.managed_instruments.instruments))
            instrument: Instrument = self.managed_instruments.instruments[instrument_id]

            if instrument.venue != venue:
                continue

            if instrument.base_currency != base_currency:
                continue

            if instrument.kind != kind:
                continue

            return instrument

    async def create_random_payload(self) -> Dict:
        """
        Creates random RFQ Create Payload.
        """
        venue: str = choice(self.supported_venues)
        kind: str = await self.choose_random_instrument_kind()
        base_currency: str = await self.choose_random_base_currency()

        is_taker_anonymous: bool = choice((True, False))
        no_legs: int = randint(1, 4)

        random_instruments: List[Instrument] = []
        for leg in range(0, no_legs):
            instrument: Instrument = await self.choose_random_instrument(
                venue=venue,
                kind=kind,
                base_currency=base_currency
                )
            random_instruments.append(instrument)
            quantity: float = instrument.min_block_size

        rfq: Dict = {
                    "venue": venue,
                    "is_taker_anonymous": is_taker_anonymous,
                    "counterparties": ["DSK94", "AAT42", "AAT44", "AAT43", "ANDY"],
                    "legs": []
                    }
        for instrument in random_instruments:
            rfq['legs'].append(
                {
                    "instrument_id": instrument.id,
                    "ratio": randint(1, 3),
                    "side": await self.create_random_side()
                }
            )

        # Add Quantity after determining composite Instruments
        rfq['quantity'] = str(quantity * randint(1, 2))
        # _quantity = float(rfq['quantity'])
        # logging.info(f'Quantity amount: {_quantity}')
        # if base_currency == 'BTC':
        #     if _quantity > 125:
        #         print('dog')
        # elif base_currency == 'ETH':
        #     if _quantity > 1250:
        #         print('dog')
        # Ensure the first leg has a Ratio of 1
        rfq['legs'][0]['ratio'] = "1"
        # Ensure the first leg is a BUY
        rfq['legs'][0]['side'] = "BUY"

        return rfq

    async def periodic_rfq_create(self) -> None:
        """
        Creates a random RFQ periodically.
        """
        # Wait for Initial Instruments request to be returned
        await self.determine_initial_instruments_request_concluded()

        self.supported_venues: List[str] = await self.determine_supported_venues()
        self.supported_base_currencies: List[str] = ['BTC', 'ETH']

        while True:
            status_code, response = await self.rest_client.post_rfq(
                    payload=await self.create_random_payload()
                    )
            if status_code != 201:
                logging.info(f'RFQ Create Status Code: {status_code} | Response: {response}')
            # rfq_id: str = response['id']
            # logging.info(f'Created RFQ ID : {rfq_id}')
            await asyncio.sleep(10)
