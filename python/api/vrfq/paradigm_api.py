import base64
from dataclasses import dataclass
from decimal import Decimal
import hmac
import json
import random
import requests
import time

MAX_RANDOM_INT = 99999999


@dataclass
class ParadigmCredential:
    access_key: str
    secret_key: str


@dataclass
class ParadigmClient:
    credential: ParadigmCredential
    host: str

    def _sign_request(self, secret_key, method, path, body):
        signing_key = base64.b64decode(secret_key)

        timestamp = str(int(time.time() * 1000)).encode('utf-8')
        message = b'\n'.join([timestamp, method.upper(), path, body])
        digest = hmac.digest(signing_key, message, 'sha256')
        signature = base64.b64encode(digest)

        return timestamp, signature

    def _build_headers(self, method: str, path: str, payload: str):
        timestamp, signature = self._sign_request(
            secret_key=self.credential.secret_key,
            method=method.encode('utf-8'),
            path=path.encode('utf-8'),
            body=payload.encode('utf-8'),
        )
        return {
            'Paradigm-API-Timestamp': timestamp,
            'Paradigm-API-Signature': signature,
            'Authorization': f'Bearer {self.credential.access_key}',
        }

    def get_rfq_data(self, id: int) -> dict:
        # TODO: expose endpoint GET /v1/vrfq/rfqs/{id}
        # GET /v1/vrfq/rfqs/
        method = 'GET'
        path = '/v1/vrfq/rfqs'
        payload = ''
        headers = self._build_headers(method, path, payload)

        response = requests.get(f"{self.host}{path}", headers=headers)
        results = response.json()['results']
        return next(rfq for rfq in results if rfq['id'] == id)

    def get_bidding_data(
        self,
        rfq_id: int,
        price: Decimal,
        wallet_name: str,
        use_nonce=False,
        use_delegated_wallet=False,
    ) -> dict:
        # POST /v1/vrfq/rfqs/{rfq_id}/pricing/
        method = 'POST'
        path = f'/v1/vrfq/rfqs/{rfq_id}/pricing/'

        payload = {
            "account": wallet_name,
            "price": str(price),
            "use_delegated_wallet": use_delegated_wallet,
        }

        if use_nonce:
            payload['nonce'] = random.randint(1, MAX_RANDOM_INT)

        json_payload = json.dumps(payload)

        headers = self._build_headers(method, path, json_payload)
        response = requests.post(f"{self.host}{path}", headers=headers, json=payload)
        return response.json()
