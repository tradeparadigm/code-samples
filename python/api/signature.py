"""
Usage:
   python3 signature.py <ACCESS KEY> <SECRET KEY>
"""


import base64
import hmac
import json
import sys
import time
from urllib.parse import urljoin

import requests


# Use credentials from command line
access_key = sys.argv[1]
secret_key = sys.argv[2]
host = 'https://api.test.paradigm.co'


def sign_request(secret_key, method, path, body):
    signing_key = base64.b64decode(secret_key)
    
    timestamp = str(int(time.time() * 1000)).encode('utf-8')
    message = b'\n'.join([timestamp, method.upper(), path, body])
    digest = hmac.digest(signing_key, message, 'sha256')
    signature = base64.b64encode(digest)
    
    return timestamp, signature


# GET example

method = b'GET'
path = b'/instruments/?page_size=1000'
body = b''

timestamp, signature = sign_request(secret_key, method, path, body)
headers = {
    'Authorization': 'Bearer {}'.format(access_key),
    'Paradigm-API-Timestamp': timestamp,
    'Paradigm-API-Signature': signature,
}
url = urljoin(host, path.decode())
response = requests.get(url, headers=headers)
print('GET response: ', response.json())


# POST example

method = b'POST'
path = b'/echo/'
data = {'message': 'hello'}
body = json.dumps(data).encode('utf-8')

timestamp, signature = sign_request(secret_key, method, path, body)
headers = {
    'Authorization': 'Bearer {}'.format(access_key),
    'Paradigm-API-Signature': signature,
    'Paradigm-API-Timestamp': timestamp,
    'Accept': 'application/json',
}
url = urljoin(host, path.decode())
response = requests.post(url, headers=headers, json=data)
print('POST response: ', response.json())
