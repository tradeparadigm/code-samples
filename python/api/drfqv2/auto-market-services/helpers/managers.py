# built ins
import asyncio
from abc import abstractmethod, ABC
from typing import Dict, List
import logging

# project
from helpers.constants import InstrumentState, RFQState, VenueInterface
from helpers.resources import RFQ, Instrument
from interface_clients.websockets import ParadigmWebSocketClient
from interface_clients.rest import ParadigmRESTClient


class ManagedInstruments:
    """
    Object to manage all known Paradigm Instruments.
    """
    def __init__(
        self,
        rest_client: ParadigmRESTClient
            ) -> None:
        self.rest_client: ParadigmRESTClient = rest_client

        # Instance Variables
        self.instruments: Dict[str, Instrument] = {}

        # Request all ACTIVE Paradigm Instruments
        asyncio.get_event_loop().create_task(
            self.get_active_instruments()
            )

        # Instantiate Periodic Instrument Hashmap update
        asyncio.get_event_loop().create_task(
            self.periodic_instrument_hashmap_update()
            )

    async def update_hashmap(
        self,
        instruments: List[Instrument]
            ) -> None:
        """
        Updates the Instrument hashmap with
        the Instruments specified.
        """
        for instrument in instruments:
            self.instruments[instrument.id] = instrument

    async def get_active_instruments(self) -> None:
        """
        - Requests all ACTIVE Paradigm Instruments.
        - Updates Instrument hashmap.
        """
        instruments: List[Instrument] = await self.rest_client.get_instruments(
            state=InstrumentState.ACTIVE
            )

        # Update Hashmap
        await self.update_hashmap(
            instruments=instruments
            )

    async def add_new_instrument(
        self,
        instrument_id: str
            ) -> None:
        """
        - Requests a specific Instrument from Paradigm.
        - Updates Instrument hashmap.
        """
        instruments: List[Instrument] = await self.rest_client.get_instrument(
            instrument_id=instrument_id
            )

        # Update Hashmap
        await self.update_hashmap(
            instruments=instruments
            )

    async def periodic_instrument_hashmap_update(self) -> None:
        """
        Periodic task to update existing Instrument hashmap.
        """
        while True:
            await asyncio.sleep(600)

            # Request all ACTIVE Instruments
            await self.get_active_instruments()


class ManagedRFQs(ABC):
    """
    Object to manage Paradigm RFQs.
    """
    def __init__(
        self,
        rest_client: ParadigmRESTClient,
        ws_client: ParadigmWebSocketClient,
        managed_instruments: ManagedInstruments
            ) -> None:
        self.rest_client: ParadigmRESTClient = rest_client
        self.ws_client: ParadigmWebSocketClient = ws_client
        self.managed_instruments: ManagedInstruments = managed_instruments

        # Instance Variables
        self.rfqs: Dict[str, RFQ] = {}

        # Request all OPEN RFQs
        asyncio.get_event_loop().create_task(
            self.get_open_rfqs()
            )

    async def _add_rfq_to_hashmap(
        self,
        rfqs: List[RFQ]
            ) -> None:
        """
        Updates RFQ hashmap.
        """
        for rfq in rfqs:
            self.rfqs[rfq.id] = rfq

    async def add_instrument_attributes_to_legs(
        self,
        rfq: RFQ
            ) -> None:
        """
        Adds the following attribute to the RFQLeg object.
        - min_tick_size
        - min_order_size_incremenet
        - min_block_size
        """
        for instrument_id, leg in rfq.legs.items():
            if instrument_id not in list(self.managed_instruments.instruments):
                await self.managed_instruments.add_new_instrument(
                    instrument_id=instrument_id
                    )
            # Add Instrument Attributes to RFQ Leg
            rfq.legs[instrument_id].add_attributes(
                instrument=self.managed_instruments.instruments[instrument_id]
                )
        return rfq

    @abstractmethod
    async def action_on_open_rfq(
        self,
        rfq_id: str
            ) -> None:
        """
        Subscribes to a WebSocket channel required
        by the users' Trade Role.
        """
        pass

    @abstractmethod
    async def action_on_closed_rfq(
        self,
        rfq_id: str
            ) -> None:
        """
        Unsubscribes to a WebSocket channel required
        by the users' Trade Role.
        """
        pass

    async def ingest_open_rfq(
        self,
        rfq: RFQ
            ) -> None:
        """
        Ingests a new OPEN RFQ.
        """
        # Adds Instrument attributes to RFQ Legs
        rfq: RFQ = await self.add_instrument_attributes_to_legs(
            rfq=rfq
            )

        # Add to RFQ hashmap
        await self._add_rfq_to_hashmap(
            rfqs=[rfq]
            )

        # Subscribe to venue_bbo.* WS Channel
        await self.action_on_open_rfq(
            rfq_id=rfq.id
            )

        logging.info(f'Ingested RFQ ID: {rfq.id}')

    async def remove_closed_rfq(
        self,
        rfq: RFQ
            ) -> None:
        """
        Removes CLOSED RFQ from hashmap.
        """
        # Remove from RFQ hashmap
        self.rfqs.pop(rfq.id, None)

        # Subscribe to venue_bbo.* WS Channel
        await self.action_on_closed_rfq(
            rfq_id=rfq.id
            )

        logging.info(f'Exgested RFQ ID: {rfq.id}')

    async def ingest_rfq_update(
        self,
        rfq: RFQ
            ) -> None:
        """
        Ingests an RFQ upate and processes appropriately.
        """
        if rfq.state == RFQState.OPEN:
            await self.ingest_open_rfq(rfq=rfq)
        else:
            await self.remove_closed_rfq(rfq=rfq)

    async def get_open_rfqs(self) -> None:
        """
        - Requests all OPEN RFQs.
        - Updates RFQ hashmap.
        """
        rfqs: List[RFQ] = await self.rest_client.get_rfqs(
            state=RFQState.OPEN
            )

        # Ingest OPEN RFQs
        for rfq in rfqs:
            asyncio.get_event_loop().create_task(
                self.ingest_rfq_update(
                    rfq=rfq
                    )
                )

    async def ingest_market_data_update(
        self,
        message: Dict
            ) -> None:
        """
        Ingests a message from the bbo.{rfq_id} WS channel
        and updates the mark price of managed RFQ legs.
        """
        rfq_id: str = message['params']['data']['rfq_id']
        hashmap: Dict[str, str] = {}
        for leg in message['params']['data']['legs']:
            hashmap[leg['instrument_id']] = leg['mark_price']
        if rfq_id in self.rfqs:
            for instrument_id, mark_price in hashmap.items():
                self.rfqs[rfq_id].legs[instrument_id].mark_price = mark_price

    async def ingest_ws_message(
        self,
        message: Dict
            ) -> None:
        """
        Ingests updates relating to RFQs, Orders, and VenueBBO.
        """
        ws_channel: str = message['params']['channel'].split('.')
        ws_channel_base: str = ws_channel[0]

        if ws_channel_base == 'rfqs':
            rfq: RFQ = RFQ()
            rfq.ingest_raw_message(
                message=message,
                venue_interface=VenueInterface.WS
                )
            await self.ingest_rfq_update(rfq=rfq)
        elif ws_channel_base == 'bbo':
            await self.ingest_market_data_update(
                message=message
                )
        elif ws_channel_base == 'orders':
            rfq_id: str = message['params']['data']['rfq_id']
            if rfq_id not in list(self.rfqs):
                return
            self.rfqs[rfq_id].ingest_order_update(
                message=message
                )
        elif ws_channel_base == 'rfq_orders':
            rfq_id: str = message['params']['data']['rfq_id']
            if rfq_id not in list(self.rfqs):
                return
            self.rfqs[rfq_id].ingest_rfq_order_update(
                message=message
                )


class MakerManagedRFQs(ManagedRFQs):
    """
    Object for the Maker to manage RFQs.
    """
    def __init__(
        self,
        rest_client: ParadigmRESTClient,
        ws_client: ParadigmWebSocketClient,
        managed_instruments: ManagedInstruments
            ) -> None:
        super().__init__(
            rest_client,
            ws_client,
            managed_instruments
            )

    async def action_on_open_rfq(
        self,
        rfq_id: str
            ) -> None:
        """
        Subscribes to a WebSocket channel required
        by the users' Trade Role.
        """
        # Subscribe to venue_bbo.* WS Channel
        await self.ws_client.create_send_ws_operation(
            channel=f'bbo.{rfq_id}',
            operation='subscribe'
            )

    async def action_on_closed_rfq(
        self,
        rfq_id: str
            ) -> None:
        """
        Unsubscribes to a WebSocket channel required
        by the users' Trade Role.
        """
        # Subscribe to venue_bbo.* WS Channel
        await self.ws_client.create_send_ws_operation(
            channel=f'bbo.{rfq_id}',
            operation='unsubscribe'
            )


class TakerManagedRFQs(ManagedRFQs):
    """
    Object for the Taker to manage RFQs.
    """
    def __init__(
        self,
        rest_client: ParadigmRESTClient,
        ws_client: ParadigmWebSocketClient,
        managed_instruments: ManagedInstruments
            ) -> None:
        super().__init__(
            rest_client,
            ws_client,
            managed_instruments
            )

    async def action_on_open_rfq(
        self,
        rfq_id: str
            ) -> None:
        """
        Subscribes to a WebSocket channel required
        by the users' Trade Role.
        """
        pass

    async def action_on_closed_rfq(
        self,
        rfq_id: str
            ) -> None:
        """
        Unsubscribes to a WebSocket channel required
        by the users' Trade Role.
        """
        pass


class ManagedMMP:
    """
    Primary class to manage MMP.
    """
    def __init__(
        self,
        rest_client: ParadigmRESTClient
            ) -> None:
        self.rest_client: ParadigmRESTClient = rest_client

        self.is_triggered: bool = False

        asyncio.get_event_loop().create_task(
            self.initial_mmp_check()
            )

    async def initial_mmp_check(self) -> None:
        """
        Checks the MMP Status of the desk and triggers off if neccessary.
        """
        self.is_triggered: bool = await self.rest_client.get_mmp()
        if self.is_triggered:
            await self.rest_client.patch_mmp()

    async def ingest_ws_message(
        self,
        message: Dict
            ) -> None:
        """
        Ingests an MMP update from Paradigm's interface.
        """
        self.is_triggered = message['params']['data']['rate_limit_hit']

        if self.is_triggered:
            await self.rest_client.patch_mmp()
