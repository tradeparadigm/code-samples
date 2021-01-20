# built ins
import base64
import hmac
import time
from urllib.parse import urljoin
import json
from random import randint

# installed
import requests

access_key = '<access-key>'
secret_key = '<secret-key>'

signing_key = base64.b64decode(secret_key)

print('Paradigm Account Access Key: {}'.format(access_key))
print('Paradigm Account Secret Key: {}'.format(signing_key))

# Request Body

host = 'https://api.test.paradigm.co'

# POST /quote/create/
method = 'POST'
path = '/quote/create/'

body = b''

client_order_id_random = randint(1, 1000000000)
# print('Client_Order_Id: {}'.format(client_order_id_random))

payload = {
            "account": {
                "name": "ParadigmTestOne"
            },
            "client_order_id": client_order_id_random,
            "expires_in": 60,
            "legs": [
                {
                    "bid_price": 39450,
                    "bid_quantity": 20000,
                    "offer_price": 39460,
                    "offer_quantity": 20000,
                    "instrument": "BTC-PERPETUAL",
                    "side": "BUY",
                    "venue": "DBT"
                }
            ],
            "rfq_id": 22539
        }

json_payload = json.dumps(payload).encode('utf-8')

message = method.encode('utf-8') + b'\n'
message += path.encode('utf-8') + b'\n'
message += json_payload

timestamp = str(int(time.time() * 1000))
message = timestamp.encode('utf-8') + b'\n' + message
digest = hmac.digest(signing_key, message, 'sha256')
signature = base64.b64encode(digest)


headers = {
            'Paradigm-API-Timestamp': timestamp,
            'Paradigm-API-Signature': signature,
            'Authorization': f'Bearer {access_key}'
            }

# Send request
response = requests.post(urljoin(host, path),
                         headers=headers,
                         json=payload)

print(response.status_code)
print(response.text)