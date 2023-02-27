# built ins
import asyncio
from random import uniform, choice, randint
from typing import Dict, List
from abc import ABC, abstractmethod
import logging

# project
from interface_clients.rest import ParadigmRESTClient
from helpers.managers import ManagedRFQs, ManagedMMP
from helpers.constants import RFQState, OrderDirection
from helpers.resources import RFQ, Order, RFQLeg, RFQOrder


class OrderManager(ABC):
    """
    Class to manage Orders around RFQs.
    """
    def __init__(
        self,
        account_name: str,
        rest_client: ParadigmRESTClient,
        managed_rfqs: ManagedRFQs,
            ) -> None:
        self.account_name: str = account_name
        self.rest_client: ParadigmRESTClient = rest_client
        self.managed_rfqs: ManagedRFQs = managed_rfqs

        # Instance Variables
        self.able_to_order_operate: bool = False

        # Instantiate Periodic Order Operation Flag
        asyncio.get_event_loop().create_task(
            self.periodic_window_flag()
            )

        # Instantiate Order Manager
        asyncio.get_event_loop().create_task(
            self.order_manager()
            )

    @abstractmethod
    async def periodic_window_flag(self) -> None:
        """
        Randomly creates and modifies able_to_order_operate
        flag as so the Order Operation coroutine knows
        when it is able to act.
        """
        pass

    @abstractmethod
    async def order_operation_request(self) -> None:
        """
        Organizes and calls the manage_order_operation_request
        coroutine for the user role in the Trade.
        """
        pass

    @abstractmethod
    async def manage_order_operation_request(
        self,
        rfq_id: str,
        order_direction: OrderDirection
            ) -> None:
        """
        - Validate if it's appropriate to submit an Order.
        - Create Order Payload.
        - Submit Order Operation to Paradigm.
        """
        pass

    @abstractmethod
    async def create_order_payload(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> Dict:
        """
        Creates Order Payload to be sent to Paradigm.
        """
        pass

    async def is_mmp_triggered(self) -> bool:
        """
        Checks if MMP has been triggered or not.
        """
        return True if self.managed_mmp.is_triggered is True else False

    async def is_rfq_active(
        self,
        rfq: RFQ
            ) -> bool:
        """
        Returns True if the RFQ is OPEN else False.
        """
        return True if rfq.state == RFQState.OPEN else False

    @abstractmethod
    async def is_order_operation_active(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> bool:
        """
        Returns True if an Order operation is already under way.
        """
        pass

    async def is_pricing_available(
        self,
        rfq: RFQ
            ) -> bool:
        """
        Checks to ensure VenueBBO data is available
        to use.
        """
        flag: bool = True
        for instrument_id, leg in rfq.legs.items():
            if not flag:
                continue

            flag = False if not leg.mark_price else True

        return flag

    async def is_rfq_order_available(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> bool:
        """
        Checks to ensure an RFQ Order on the side is available.
        """
        return True if rfq.rfq_orders[order_direction] else False

    async def is_create_operation(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> bool:
        """
        Determines if the system needs to send a CREATE or REPLACE
        order operation.
        """
        return True if not rfq.orders[order_direction].order_id else False

    async def create_leg_price(
        self,
        leg: RFQLeg,
        order_direction: OrderDirection = OrderDirection.BUY
            ) -> float:
        """
        Creates a leg price depending upon the
        order_pricing_tick_multiple env variable.
        """
        if leg.hedge_leg_flag:
            return leg.price
        else:
            random_multiple: int = randint(
                self.order_pricing_tick_multiple / 2,
                self.order_pricing_tick_multiple
                )
            if leg.side == OrderDirection.BUY:
                price: float = float(leg.mark_price) - (random_multiple * float(leg.min_tick_size))

                if leg.sell_order_price:
                    if price <= leg.sell_order_price:
                        price = leg.sell_order_price - (random_multiple * float(leg.min_tick_size))
            else:
                price: float = float(leg.mark_price) + (random_multiple * float(leg.min_tick_size))

                if leg.buy_order_price:
                    if price >= leg.buy_order_price:
                        price = leg.buy_order_price + (random_multiple * float(leg.min_tick_size))

            if price <= 0:
                price = float(leg.mark_price)
                if price <= 0:
                    price = float(leg.min_tick_size)
            return round(price, leg.price_precision)

    async def order_manager(self) -> None:
        """
        Long running coroutine that:
        - Creates Order Payloads
        - Submits Order Operations to Paradigm.
        """
        while True:
            # Checks if time window permits or there are ManagedRFQs
            if not self.able_to_order_operate or not self.managed_rfqs.rfqs:
                await asyncio.sleep(0)
                continue

            await self.order_operation_request()

            await asyncio.sleep(0.01)


class MakerOrderManager(OrderManager):
    """
    Class to manage all of the Maker's Order interactions.
    """
    def __init__(
        self,
        account_name: str,
        rest_client: ParadigmRESTClient,
        order_price_worse_than_mark_flag: bool,
        order_pricing_tick_multiple: int,
        order_refresh_window_lower_boundary: float,
        order_refresh_window_upper_boundary: float,
        managed_rfqs: ManagedRFQs,
        managed_mmp: ManagedMMP
            ) -> None:
        super().__init__(
            account_name,
            rest_client,
            managed_rfqs
            )
        self.order_price_worse_than_mark_flag: bool = order_price_worse_than_mark_flag
        self.order_pricing_tick_multiple: int = order_pricing_tick_multiple
        self.order_refresh_window_lower_boundary: int = order_refresh_window_lower_boundary
        self.order_refresh_window_upper_boundary: int = order_refresh_window_upper_boundary
        self.managed_mmp: ManagedMMP = managed_mmp

    async def periodic_window_flag(self) -> None:
        """
        Randomly creates and modifies able_to_order_operate
        flag as so the Order Operation coroutine knows
        when it is able to act.
        """
        while True:
            window: float = uniform(
                self.order_refresh_window_lower_boundary,
                self.order_refresh_window_upper_boundary
                )

            self.able_to_order_operate = True

            await asyncio.sleep(window)

    async def is_order_operation_active(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> bool:
        """
        Returns True if an Order operation is already under way.
        """
        order: Order = rfq.orders[order_direction]
        return True if order.order_operation_flag else False

    async def order_operation_request(self) -> None:
        """
        Organizes and calls the manage_order_operation_request
        coroutine for the user role in the Trade.
        """
        for rfq_id, rfq in self.managed_rfqs.rfqs.items():
            # Randomize Order side operated upon
            first_side: OrderDirection = choice(list(OrderDirection))
            second_side: OrderDirection = OrderDirection.BUY if first_side == OrderDirection.SELL else OrderDirection.SELL
            sides_order: List[OrderDirection] = [first_side, second_side]

            for side in sides_order:
                asyncio.get_event_loop().create_task(
                    self.manage_order_operation_request(
                        rfq_id=rfq_id,
                        order_direction=side
                        )
                    )

        # Trigger off ability to Order Operate until
        # Pricing Window triggers it back on
        self.able_to_order_operate = False

    async def manage_order_operation_request(
        self,
        rfq_id: str,
        order_direction: OrderDirection
            ) -> None:
        """
        - Validate if it's appropriate to submit an Order.
        - Create Order Payload.
        - Submit Order Operation to Paradigm.
        """
        if await self.is_mmp_triggered():
            return None

        if rfq_id not in list(self.managed_rfqs.rfqs):
            return None
        else:
            rfq: RFQ = self.managed_rfqs.rfqs[rfq_id]

        if not await self.is_rfq_active(
            rfq=rfq
                ):
            return None

        if await self.is_order_operation_active(
            rfq=rfq,
            order_direction=order_direction
                ):
            return None

        if not await self.is_pricing_available(
            rfq=rfq
                ):
            return None

        order_payload: Dict = await self.create_order_payload(
            rfq=rfq,
            order_direction=order_direction
            )

        is_create_operation: bool = await self.is_create_operation(
            rfq=rfq,
            order_direction=order_direction
            )

        if rfq_id not in list(self.managed_rfqs.rfqs):
            return None

        self.managed_rfqs.rfqs[rfq_id].orders[order_direction].order_operation_flag = True

        if is_create_operation:
            status_code, response = await self.rest_client.post_orders(
                payload=order_payload
                )
            # logging.info(f'RFQ ID: {rfq_id} | Create {order_direction.name} Order | Status Code: {status_code}')
        else:
            status_code, response = await self.rest_client.put_orders_replace(
                payload=order_payload,
                order_id=rfq.orders[order_direction].order_id
                )
            # logging.info(f'RFQ ID: {rfq_id} | Replace {order_direction.name} Order | Status Code: {status_code}')

        if status_code == 400:
            if response['code'] in [3009, 3001]:
                self.managed_rfqs.rfqs[rfq_id].orders[order_direction].reset_order_id()
            elif response['code'] in [2001]:
                if rfq_id in list(self.managed_rfqs.rfqs):
                    await self.managed_rfqs.remove_closed_rfq(
                        rfq=self.managed_rfqs.rfqs[rfq_id]
                        )
            elif response['code'] in [3504]:
                pass
            else:
                logging.info(f'Is Create Request: {is_create_operation}')
                logging.info(f'Status Code: {status_code} | Response: {response}')

        if rfq_id not in list(self.managed_rfqs.rfqs):
            return None

        self.managed_rfqs.rfqs[rfq_id].orders[order_direction].order_operation_flag = False

    async def create_order_payload(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> Dict:
        """
        Creates Order Payload to be sent to Paradigm.
        """
        # Base
        order_payload: Dict = {
                                "rfq_id": rfq.id,
                                "account_name": self.account_name,
                                "label": "hmm",
                                "type": "LIMIT",
                                "time_in_force": "GOOD_TILL_CANCELED",
                                "legs": [],
                                "quantity": rfq.quantity,
                                "side": order_direction.name
                                }
        # Add legs to Order Payload
        for instrument_id, leg in self.managed_rfqs.rfqs[rfq.id].legs.items():
            price: float = await self.create_leg_price(
                order_direction=order_direction,
                leg=leg
                )
            self.managed_rfqs.rfqs[rfq.id].legs[instrument_id].update_order_price(
                order_direction=order_direction,
                order_price=price
                )
            order_payload['legs'].append(
                {
                    'instrument_id': instrument_id,
                    'price': price
                }
                )
        return order_payload


class TakerOrderManager(OrderManager):
    """
    Class to manage all of the Maker's Order interactions.
    """
    def __init__(
        self,
        account_name: str,
        rest_client: ParadigmRESTClient,
        managed_rfqs: ManagedRFQs,
            ) -> None:
        super().__init__(
            account_name,
            rest_client,
            managed_rfqs
            )

        # Instance Variables
        self.order_operation_count: int = 0

    async def increment_order_operation_count(self) -> None:
        """
        Increments the order_operation_count variable as well as
        toggles the able_to_order_operate variable.
        """
        self.order_operation_count += 1

        if self.order_operation_count >= 2:
            self.able_to_order_operate = False

    async def periodic_window_flag(self) -> None:
        """
        Randomly creates and modifies able_to_order_operate
        flag as so the Order Operation coroutine knows
        when it is able to act.

        Takers are only able to execute 2 times every 5 seconds.
        """
        while True:
            self.able_to_order_operate = True
            await asyncio.sleep(5)

    async def is_order_operation_active(
        self,
        rfq: RFQ
            ) -> bool:
        """
        Returns True if an Order operation is already under way.
        """
        return True if rfq.order_operation_flag else False

    async def order_operation_request(self) -> None:
        """
        Organizes and calls the manage_order_operation_request
        coroutine for the user role in the Trade.
        """
        pass
        # for rfq_id, rfq in self.managed_rfqs.rfqs.items():
        #     # Randomize Order side operated upon
        #     side: OrderDirection = choice(list(OrderDirection))

        #     asyncio.get_event_loop().create_task(
        #         self.manage_order_operation_request(
        #             rfq_id=rfq_id,
        #             order_direction=side
        #             )
        #         )

    async def pick_random_rfq_order_price(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> str:
        """
        Picks a random RFQ Order from an RFQ and returns the price.
        """
        if rfq.rfq_orders[order_direction] == {}:
            return None
        rfq_order_id: str = choice(list(rfq.rfq_orders[order_direction]))
        rfq_order: RFQOrder = rfq.rfq_orders[order_direction][rfq_order_id]
        return rfq_order.price

    async def create_order_payload(
        self,
        rfq: RFQ,
        order_direction: OrderDirection
            ) -> Dict:
        """
        Creates Order Payload to be sent to Paradigm.
        """
        random_rfq_order_price: str = await self.pick_random_rfq_order_price(
            rfq=rfq,
            order_direction=order_direction
            )
        if not random_rfq_order_price:
            return None

        side: OrderDirection = OrderDirection.BUY if order_direction.SELL else order_direction.BUY

        return {
                "rfq_id": rfq.id,
                "account_name": self.account_name,
                "label": "mmh",
                "type": "LIMIT",
                "time_in_force": "FILL_OR_KILL",
                "price": random_rfq_order_price,
                "quantity": rfq.quantity,
                "side": side.name
                }

    async def manage_order_operation_request(
        self,
        rfq_id: str,
        order_direction: OrderDirection
            ) -> None:
        """
        - Validate if it's appropriate to submit an Order.
        - Create Order Payload.
        - Submit Order Operation to Paradigm.
        """
        if rfq_id not in list(self.managed_rfqs.rfqs):
            return None
        else:
            rfq: RFQ = self.managed_rfqs.rfqs[rfq_id]

        if not await self.is_rfq_active(
            rfq=rfq
                ):
            return None

        if await self.is_order_operation_active(
            rfq=rfq
                ):
            return None

        if not await self.is_rfq_order_available(
            rfq=rfq,
            order_direction=order_direction
                ):
            return None

        await asyncio.sleep(10)

        order_payload: Dict = await self.create_order_payload(
            rfq=rfq,
            order_direction=order_direction
            )
        # If the RFQ Orders is no longer available with a price
        if not order_payload:
            return None

        if rfq_id not in list(self.managed_rfqs.rfqs):
            return None

        self.managed_rfqs.rfqs[rfq_id].order_operation_flag = True

        status_code, response = await self.rest_client.post_orders(
            payload=order_payload
            )
        # logging.info(f'RFQ ID: {rfq_id} | Create {order_direction.name} Order | Status Code: {status_code}')

        if status_code == 201:
            await self.increment_order_operation_count()

        # if status_code == 400:
        #     logging.info(f'Status Code: {status_code} | Response: {response}')

        if rfq_id not in list(self.managed_rfqs.rfqs):
            return None

        self.managed_rfqs.rfqs[rfq_id].order_operation_flag = False
