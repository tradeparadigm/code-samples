"""
    Venue RESToverHTTP interface client to interact with Paradigm.
"""

# built ins
import asyncio
import os
from abc import ABC
from typing import Dict, Tuple, List, Optional
import time
import base64
import hmac
import json
import logging

# installed
import aiohttp

# project
from helpers.constants import RFQState, InstrumentState, \
     VenueInterface, OrderState
from helpers.resources import RFQ, Instrument


class VenueRESTClient(ABC):
    def __init__(
        self,
        connection_url: str,
        access_key: str,
        secret_key: str
            ) -> None:
        self.connection_url: str = connection_url
        self.access_key: str = access_key
        self.secret_key: str = secret_key

    async def _get_request(
        self,
        endpoint: str,
        headers: Dict,
        cursor: str = None
            ) -> Tuple[int, Dict]:
        """
        Aysnc method for [GET] requests.

        Returns HTTP Status Code and Response.
        """
        async with aiohttp.ClientSession() as session:
            try:
                url: str = f'{self.connection_url}{endpoint}'
                if cursor:
                    url += f'?{cursor}'
                async with session.get(
                    url,
                    headers=headers
                        ) as response:
                    status_code: int = response.status
                    response: Dict = await response.json()
            finally:
                await session.close()
        return status_code, response

    async def _post_request(
        self,
        endpoint: str,
        headers: Dict,
        payload: Dict
            ) -> Tuple[int, Dict]:
        """
        Aysnc method for [POST] requests.

        Returns HTTP Status Code and Response.
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.connection_url+endpoint,
                    headers=headers,
                    json=payload
                        ) as response:
                    status_code: int = response.status
                    response: Dict = await response.json()
            except aiohttp.ContentTypeError:
                logging.info(f'POST request Error | Status Code: {status_code}')
            finally:
                await session.close()
        return status_code, response

    async def _put_request(
        self,
        endpoint: str,
        headers: Dict,
        payload: Dict
            ) -> Tuple[int, Dict]:
        """
        Aysnc method for [PUT] requests.

        Returns HTTP Status Code and Response.
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.put(
                    self.connection_url+endpoint,
                    headers=headers,
                    json=payload
                        ) as response:
                    status_code: int = response.status
                    response: Dict = await response.json()
            except aiohttp.ClientConnectionError:
                response: Dict = {}
                logging.info(f'PUT Request ClientConnectionError Status Code: {status_code}')
            except aiohttp.ClientConnectorError:
                response: Dict = {}
                logging.info(f'PUT Request ClientConnectorError Status Code: {status_code}')
            except aiohttp.ContentTypeError:
                response: Dict = {}
                logging.info(f'PUT Request ContentTypeError Status Code: {status_code}')
            finally:
                await session.close()
        return status_code, response

    async def _patch_request(
        self,
        endpoint: str,
        headers: Dict,
        payload: Dict
            ) -> Tuple[int, Dict]:
        """
        Aysnc method for [PATCH] requests.

        Returns HTTP Status Code and Response.
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.patch(
                    self.connection_url+endpoint,
                    headers=headers,
                    json=payload
                        ) as response:
                    status_code: int = response.status
                    response: Dict = await response.json()
            finally:
                await session.close()
        return status_code, response


class ParadigmRESTClient(VenueRESTClient):
    def _create_signature(
        self,
        method: str,
        endpoint: str,
        payload: Dict = ''
            ) -> Tuple[int, str]:
        """
        Creates the Signature and Timestamp required
        for each Paradigm REST request.
        """
        method: str = method.encode('utf-8')
        path: str = endpoint.encode('utf-8')

        if payload:
            payload = json.dumps(payload)

        body: str = payload.encode('utf-8')

        signing_key = base64.b64decode(self.secret_key)
        timestamp = str(int(time.time() * 1000)).encode('utf-8')
        message = b'\n'.join([timestamp, method.upper(), path, body])
        digest = hmac.digest(signing_key, message, 'sha256')
        signature = base64.b64encode(digest)
        return timestamp, signature

    def create_headers(
        self,
        method: str,
        endpoint: str,
        payload: Dict = ''
            ) -> Dict:
        """
        Creates the REST request Header required for
        each Paradigm REST request.
        """
        timestamp, signature = self._create_signature(
            method=method,
            endpoint=endpoint,
            payload=payload
            )

        return {
                'Paradigm-API-Timestamp': timestamp.decode('utf-8'),
                'Paradigm-API-Signature': signature.decode('utf-8'),
                'Authorization': f'Bearer {self.access_key}'
                }

    async def paginate_endpoint(
        self,
        method: str,
        endpoint: str
            ) -> List[Dict]:
        """
        Paginates the requested endpoint and returns
        the raw responses until no more are available.
        """
        # Initial Request
        headers: Dict = self.create_headers(
            method=method,
            endpoint=endpoint
            )

        status_code, response = await self._get_request(
            endpoint=endpoint,
            headers=headers
            )
        if status_code != 200:
            logging.info(f'{method} {endpoint} | Status Code: {status_code}')
            return []

        result: List[Dict] = [x for x in response['results']]
        cursor: str = response['next']

        # Paginated Requests
        while cursor is not None:
            await asyncio.sleep(1)
            cursor_endpoint: str = f'{endpoint}&cursor={cursor}'
            headers: Dict = self.create_headers(
                method=method,
                endpoint=cursor_endpoint
                )

            status_code, response = await self._get_request(
                endpoint=cursor_endpoint,
                headers=headers
                )

            if status_code != 200:
                logging.info(f'{method} {endpoint} | Status Code: {status_code}')
                return []

            for element in response['results']:
                result.append(element)
            cursor: str = response['next']
        return result

    async def get_instruments(
        self,
        state: Optional[InstrumentState] = None
            ) -> List[Instrument]:
        """
        Requests and paginates the [GET] /instruments endpoint.
        """
        method: str = 'GET'
        endpoint: str = '/v2/drfq/instruments'

        if state:
            endpoint = f'{endpoint}?page_size=100&state={state.name}&include_greeks=True'
        else:
            endpoint = f'{endpoint}?page_size=100&include_greeks=True'

        # endpoint += '&kind=OPTION&base_currency=BTC&venue=DBT'

        results: List[Dict] = await self.paginate_endpoint(
            method=method,
            endpoint=endpoint
            )

        instruments: List[Instrument] = []
        for instrument in results:
            _instrument: Instrument = Instrument()
            _instrument.ingest_raw_message(
                message=instrument
                )
            instruments.append(_instrument)

        return instruments

    async def get_instrument(
        self,
        instrument_id: str
            ) -> List[Instrument]:
        """
        Requests the [GET] /intruments/{instrument_id} endpoint.
        """
        method: str = 'GET'
        endpoint: str = f'/v2/drfq/instruments/{instrument_id}'

        headers: Dict = self.create_headers(
            method=method,
            endpoint=endpoint
            )

        status_code, response = await self._get_request(
            endpoint=endpoint,
            headers=headers
            )

        if status_code != 200:
            logging.info(f'{method} {endpoint} | Status Code: {status_code}')
            return []

        instrument: Instrument = Instrument()
        instrument.ingest_raw_message(
            message=response
            )
        return [instrument]

    async def get_rfqs(
        self,
        state: Optional[RFQState] = None
            ) -> List[RFQ]:
        """
        Requests and paginates the [GET] /rfqs endpoint.
        """
        method: str = 'GET'
        endpoint: str = '/v2/drfq/rfqs'

        if state:
            endpoint = f'{endpoint}?page_size=100&state={state.name}'
        else:
            endpoint = f'{endpoint}?page_size=100'

        results: List[Dict] = await self.paginate_endpoint(
            method=method,
            endpoint=endpoint
            )

        rfqs: List[RFQ] = []
        for rfq in results:
            _rfq: RFQ = RFQ()
            _rfq.ingest_raw_message(
                message=rfq,
                venue_interface=VenueInterface.REST
                )
            rfqs.append(_rfq)

        return rfqs

    async def post_rfq(
        self,
        payload: Dict
            ) -> None:
        """
        Request the [POST] /rfqs endpoint.
        """
        method: str = 'POST'
        endpoint: str = '/v2/drfq/rfqs'

        headers: Dict = self.create_headers(
            method=method,
            endpoint=endpoint,
            payload=payload
            )

        return await self._post_request(
            endpoint=endpoint,
            headers=headers,
            payload=payload
            )

    async def post_orders(
        self,
        payload: Dict
            ) -> None:
        """
        Requests the [POST] /orders endpoint.
        """
        method: str = 'POST'
        endpoint: str = '/v2/drfq/orders'

        headers: Dict = self.create_headers(
            method=method,
            endpoint=endpoint,
            payload=payload
            )

        return await self._post_request(
            endpoint=endpoint,
            headers=headers,
            payload=payload
            )

    async def put_orders_replace(
        self,
        payload: Dict,
        order_id: str
            ) -> None:
        """
        Requests the [PUT] /orders/{order_id} endpoint.
        """
        method: str = 'PUT'
        endpoint: str = f'/v2/drfq/orders/{order_id}'

        headers: Dict = self.create_headers(
            method=method,
            endpoint=endpoint,
            payload=payload
            )

        return await self._put_request(
            endpoint=endpoint,
            headers=headers,
            payload=payload
            )

    async def get_orders(
        self,
        state: Optional[OrderState] = None
            ) -> List[RFQ]:
        """
        Requests and paginates the [GET] /rfqs endpoint.
        """
        method: str = 'GET'
        endpoint: str = '/v2/drfq/orders'

        if state:
            endpoint = f'{endpoint}?page_size=100&state={state.name}'
        else:
            endpoint = f'{endpoint}?page_size=100'

        results: List[Dict] = await self.paginate_endpoint(
            method=method,
            endpoint=endpoint
            )

        return results

    async def get_mmp(self) -> bool:
        """
        Requests and paginates the [GET] /mmp/status endpoint.
        """
        method: str = 'GET'
        endpoint: str = '/v2/drfq/mmp/status'

        headers: Dict = self.create_headers(
            method=method,
            endpoint=endpoint
            )

        status_code, response = await self._get_request(
            endpoint=endpoint,
            headers=headers
            )

        if status_code == 200:
            return response['rate_limit_hit']
        else:
            return True

    async def patch_mmp(self) -> None:
        """
        Requests the [PATCH] /mmp/status endpoint.
        """
        method: str = 'PUT'
        endpoint: str = '/v2/drfq/mmp/status'

        headers: Dict = self.create_headers(
            method=method,
            endpoint=endpoint
            )

        return await self._patch_request(
            endpoint=endpoint,
            headers=headers,
            payload=''
            )

# client = ParadigmRESTClient(
#     connection_url='https://api.nightly.paradigm.trade',
#     access_key=os.environ['ACCESS_KEY'],
#     secret_key=os.environ['SECRET_KEY']
#     )
# loop = asyncio.get_event_loop()
# loop.run_until_complete(client.get_rfqs(state=RFQState.OPEN))
