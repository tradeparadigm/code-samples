# built ins
from typing import Dict

# project
from helpers.constants import InstrumentState, RFQState, \
     OrderDirection, VenueInterface


class RFQOrder:
    """
    Object to represent a Paradigm RFQ Order.
    """
    def __init__(
        self,
        id: str,
        rfq_id: str,
        order_direction: OrderDirection,
        price: str,
        quantity: str
            ) -> None:
        self.id: str = id
        self.rfq_id: str = rfq_id
        self.order_direction: OrderDirection = order_direction
        self.price: str = price
        self.quantity: str = quantity


class Order:
    """
    Object to represent a Paradigm Order.
    """
    def __init__(
        self,
        rfq_id: str,
        order_direction: OrderDirection
            ) -> None:
        self.rfq_id: str = rfq_id
        self.order_direction: OrderDirection = order_direction

        # Instance Variables
        self.order_id: str = None
        self.order_operation_flag: bool = False
        self.created_at: float = None

    def reset_order_id(self) -> None:
        """
        Sets the order_id instance attribute to None.
        Used in the case of code == 3009 errors.
        """
        self.order_id = None


class Instrument:
    """
    Object to represent a Paradigm Instrument.
    """
    def ingest_raw_message(
        self,
        message: Dict
            ) -> None:
        """
        Ingests an INSTRUMENT object.
        """
        self.id: int = message['id']
        self.name: str = message['name']
        self.venue: str = message['venue']
        self.kind: str = message['kind']
        self.base_currency: str = message['base_currency']
        self.expires_at: float = message['expires_at']
        self.venue_name: str = message['venue_instrument_name']
        self.min_tick_size: float = message['min_tick_size']
        self.min_order_size_increment: float = float(message['min_order_size_increment'])
        self.min_block_size: float = message['min_block_size']
        self.state: InstrumentState = InstrumentState[message['state']]

        if 'greeks' in list(message):
            if not message['greeks']:
                self.mark_price: None = None
            else:
                self.mark_price: float = float(message['greeks']['mark_price'])
        else:
            self.mark_price: None = None

        # Instance Variables
        self.price_precision: int = self.calculate_price_precision(
            min_tick_size=self.min_tick_size
            )

    def calculate_price_precision(
        self,
        min_tick_size: float
            ) -> int:
        """
        Determines the number of decimal places from
        the min_tick_size attribute of the Instrument.
        """
        return len(str(min_tick_size).split('.')[1])


class RFQLeg:
    """
    Object to represent a Paradigm RFQ Leg.
    """
    def ingest_raw_message(
        self,
        message: Dict
            ) -> None:
        self.id: int = message['instrument_id']
        self.side: OrderDirection = OrderDirection[message['side']]
        if 'price' in list(message):
            self.hedge_leg_flag: bool = True
            self.price: float = message['price']
        else:
            self.hedge_leg_flag: bool = False
            self.price: None = None

        # BBO
        self.mark_price: float = ''
        self.min_price: float = ''
        self.max_price: float = ''

    def add_attributes(
        self,
        instrument: Instrument
            ) -> None:
        """
        Adds Instrument attributes to the RFQLeg object
        to ensure the OrderManager can price appropriately.
        """
        self.min_tick_size: float = instrument.min_tick_size
        self.min_order_size_increment: float = instrument.min_order_size_increment
        self.min_block_size: float = instrument.min_block_size
        self.price_precision: int = instrument.price_precision

    def update_bbo(
        self,
        message: Dict
            ) -> Dict:
        """

        """
        self.mark_price: float = ''
        self.min_price: float = ''
        self.max_price: float = ''


class RFQ:
    """
    Object to manage a Paradigm RFQ.
    """
    def __init__(self) -> None:
        self.order_operation_flag: bool = False

    def ingest_raw_message(
        self,
        message: Dict,
        venue_interface: VenueInterface
            ) -> None:
        """
        Ingests a raw RFQ object.
        """
        if venue_interface == VenueInterface.WS:
            message = message['params']['data']

        self.id: str = message['id']
        self.state: RFQState = RFQState[message['state']]
        self.quantity: str = message['quantity']
        self.side_layering_limit: int = message['side_layering_limit']
        self.legs: Dict[str, RFQLeg] = {}
        for leg in message['legs']:
            rfq_leg: RFQLeg = RFQLeg()
            rfq_leg.ingest_raw_message(
                message=leg
                )
            self.legs[rfq_leg.id] = rfq_leg

        self.orders: Dict[OrderDirection, Order] = self.create_user_orders()

        self.rfq_orders: Dict[OrderDirection, Dict[str, RFQOrder]] = self.create_rfq_orders()

    def create_user_orders(self) -> Dict[OrderDirection, Order]:
        """
        Creates the BUY and SELL Order for the RFQ.
        """
        orders: Dict[OrderDirection, Order] = {}

        # BUY Order
        orders[OrderDirection.BUY] = Order(
            rfq_id=self.id,
            order_direction=OrderDirection.BUY
            )

        # SELL Order
        orders[OrderDirection.SELL] = Order(
            rfq_id=self.id,
            order_direction=OrderDirection.SELL
            )
        return orders

    def create_rfq_orders(self) -> Dict[OrderDirection, Dict[str, RFQOrder]]:
        """
        Creates a BUY and SELL hashmap to store all
        RFQ Orders updates.
        """
        return {
                OrderDirection.BUY: {},
                OrderDirection.SELL: {}
                }

    def ingest_order_update(
        self,
        message: Dict
            ) -> None:
        """
        Ingests an update about an Order for the user.
        """
        order_direction: OrderDirection = OrderDirection[message['params']['data']['side']]

        self.orders[order_direction].created_at = message['params']['data']['created_at']
        self.orders[order_direction].order_id = message['params']['data']['id']

    def ingest_rfq_order_update(
        self,
        message: Dict
            ) -> None:
        """
        Ingests an update about an RFQ's Orders for the user.
        """
        id: str = message['params']['data']['id']
        rfq_id: str = message['params']['data']['rfq_id']
        order_direction: OrderDirection = OrderDirection[message['params']['data']['side']]
        price: str = message['params']['data']['price']
        quantity: str = message['params']['data']['quantity']

        rfq_order: RFQOrder = RFQOrder(
            id=id,
            rfq_id=rfq_id,
            order_direction=order_direction,
            price=price,
            quantity=quantity
            )

        event: str = message['params']['event']

        if event == 'REMOVED':
            if id in (self.rfq_orders[order_direction]):
                self.rfq_orders[order_direction].pop(id)
        else:
            self.rfq_orders[order_direction][id] = rfq_order
