"""
Usage:
   python3 POST-rfq_create_rfs.py <ACCESS KEY> <SECRET KEY>
                                  <PARADIGM_API_KEY_NAME>
"""

import base64
import hmac
import time
from urllib.parse import urljoin
import json
import sys
from random import randint

import requests

if len(sys.argv) == 3:
    access_key = sys.argv[1]
    secret_key = sys.argv[2]
    paradigm_api_key_name = sys.argv[3]
else:
    # Local Testing
    access_key = 'stNlMtdDmil3KmWsG3FUaSYu'
    secret_key = 'F9XyAVqq9BaA1xbPVoKlxwv0j/+SIZZjpizcwEzy7eTkugCN'
    paradigm_api_key_name = "ParadigmTestOne"

host = 'https://api.test.paradigm.co'

signing_key = base64.b64decode(secret_key)

print('Paradigm Account Access Key: {}'.format(access_key))
print('Paradigm Account Secret Key: {}'.format(signing_key))


# POST /rfq/create/
method = 'POST'
path = '/rfq/create/'

body = b''

client_order_id_random = randint(1, 1000000000)
# print('Client_Order_Id: {}'.format(client_order_id_random))

payload = {
            "account": {
                        "name": paradigm_api_key_name
                        },
            "client_order_id": client_order_id_random,
            "stream": True,
            "legs": [
                    {
                        "side": "BUY",
                        "instrument": "BTC-29JAN21-34000-C",
                        "venue": "DBT"
                    }
                    ]
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
