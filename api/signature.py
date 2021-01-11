"""
Usage:
   python3 signature.py <API KEY> <SECRET KEY>
"""


import base64
import hashlib
import hmac
import json
import time
import requests
import sys

# Use credentials from command line
access_key = sys.argv[1]
secret_key = sys.argv[2]

signing_key = base64.b64decode(secret_key)


# GET example
host = 'https://api.test.paradigm.co'
method = 'GET'
path = '/instruments/?page_size=1000'
body = b''
message = method.encode('utf-8') + b'\n'
message += path.encode('utf-8') + b'\n'
message += body
timestamp = str(int(time.time() * 1000))
timestamp = '1610359155205'
message = timestamp.encode('utf-8') + b'\n' + message
digest = hmac.digest(signing_key, message, 'sha256')
signature = base64.b64encode(digest)
headers = {
    'Paradigm-API-Timestamp': timestamp,
    'Paradigm-API-Signature': signature,
    'Authorization': 'Bearer ' + access_key
}
r = requests.get(host + path, headers=headers)
print('GET response: ', r.json())


# POST example
request_params = b''
request_url = b'/echo/'
request_method = b'POST'
request_data = {'message': 'hello'}
request_body = json.dumps(request_data).encode('utf-8')

key = base64.b64decode(secret_key)
timestamp = str(int(time.time() * 1000)).encode('utf-8')

message = b'\n'.join([timestamp, request_method, request_url, request_body])
digest = hmac.digest(key, message, hashlib.sha256)
signature = base64.b64encode(digest)

headers = {
  'Accept': 'application/json',
  'Authorization': 'Bearer ' + access_key,
  'Paradigm-API-Signature': signature,
  'Paradigm-API-Timestamp': timestamp
}

r = requests.post(
    'https://api.test.paradigm.co/echo/',
    headers=headers,
    json=request_data,
)
print('POST response: ', r.json())
