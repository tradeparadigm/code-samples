# built ins
import base64
import hmac
import time
from urllib.parse import urljoin

# installed
import requests


access_key = '<access-key>'
secret_key = '<secret-key>'

signing_key = base64.b64decode(secret_key)

print('Paradigm Account Access Key: {}'.format(access_key))
print('Paradigm Account Secret Key: {}'.format(signing_key))

# Request Body

host = 'https://api.test.paradigm.co'

# GET /counterparties/
method = 'GET'
path = '/counterparties/'

body = b''

message = method.encode('utf-8') + b'\n'
message += path.encode('utf-8') + b'\n'

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
response = requests.get(urljoin(host, path),
                        headers=headers)

print(response.status_code)
print(response.text)
