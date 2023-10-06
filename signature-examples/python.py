
import base64
import hmac
import json
import time
from urllib.parse import urljoin

import requests


access_key="<your key here>"
secret_key='<your secret here>'

host="https://api.testnet.paradigm.trade"
path='/v1/echo'
method='GET'
data = {}
payload = json.dumps(data).encode('utf-8')


def sign_request(secret_key, method, path, body):
    signing_key = base64.b64decode(secret_key)
    print("Signing key:", signing_key)
    timestamp = str(int(time.time() * 1000))
    message = b'\n'.join([timestamp.encode(), method.upper().encode(), path.encode(), body])
    print("Message:", message)
    digest = hmac.digest(signing_key, message, 'sha256')
    signature = base64.b64encode(digest)
    print("Signature", signature)
    return timestamp, signature

timestamp, signature = sign_request(secret_key, method, path, payload)
headers = {
    'Authorization': f'Bearer {access_key}',
    'Paradigm-API-Signature': signature,
    'Paradigm-API-Timestamp': timestamp,
    'Accept': 'application/json',
}

url = urljoin(host, path)
response = requests.get(url, headers=headers, json=data)
print(response.status_code)
print(response.text)