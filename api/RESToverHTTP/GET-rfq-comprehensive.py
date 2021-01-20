"""
Paradigm REST over HTTP script that allows you to GET RFQs.

Run the script and provide the arguements to suit. The script will
automatically paginate and return all results until out of pages.

Usage:
    python3 GetRFQ.py [RFQ_ID] [CLIENT_ORDER_ID] [PAGE] [STATUS] [ACCESS KEY] [SECRET KEY]

Requirements:
    pip3 install requests
"""

# built ins
import base64
import hmac
import time
from urllib.parse import urljoin
import json
import argparse

# installed
import requests

class ParadigmRestClient():
    def __init__(self, rfq_id=None, client_order_id=None, 
                 page=None, status=None,
                 access_key=None, secret_key=None, host=None):
        # User Credentials
        self.access_key = access_key
        self.signing_key = secret_key

        # Arguments
        self.rfq_id = rfq_id
        self.client_order_id = client_order_id
        self.page = float(page)
        self.status = status

        # Initlize Requests Session
        self.session = requests.Session()

        if host:
            self.host = host
        else:
            self.host = 'https://api.test.paradigm.co'

    def request(self, action=None, data=None, method=None):
        
        # Include rfq_id if specified
        if self.rfq_id != "-1":
            action += '?rfq_id={}&'.format(self.rfq_id)

        # Include client_order_id if specified
        if self.client_order_id != "-1":
            action += '?client_order_id={}&'.format(self.client_order_id)

        # Include page if specified
        if self.page != -1:
            action += '?page={}&'.format(self.page)

        # Include status if specified
        if self.status != "-1":
            action += '?status={}&'.format(self.status)

        # Generate Signature
        signature, timestamp = self.generate_signature(action=action,
                                                       method=method)

        # HTTP Request Headers
        headers = {
                    'Paradigm-API-Timestamp': timestamp,
                    'Paradigm-API-Signature': signature,
                    'Authorization': f'Bearer {self.access_key}'
                    }

        # GET Request
        response = requests.get(urljoin(self.host, action),
                                headers=headers)

        # Check response code for error
        if response.status_code != 200 and response.status_code != 201:
            print('Incorrect response code: {0}'.format(response.status_code))

        print('Response Status Code: {}'.format(response.status_code))
        print('Response Text:')
        print(response.text)

        # To paginate the returned results and ensure all results are returned
        page_check = json.loads(response.text)['next']

        if page_check is not None:
            if page_check > self.page:
                self.page = page_check
                self.get_rfq()

    def generate_signature(self, action, method):
        message = method.encode('utf-8') + b'\n'
        message += action.encode('utf-8') + b'\n'

        timestamp = str(int(time.time() * 1000))
        message = timestamp.encode('utf-8') + b'\n' + message
        digest = hmac.digest(self.signing_key, message, 'sha256')
        signature = base64.b64encode(digest)

        return signature, timestamp

    def get_rfq(self):
        return self.request(action='/rfq/', method='GET')


if __name__ == "__main__":
    # Arguments
    my_parser = argparse.ArgumentParser()

    my_parser.add_argument('RFQ_ID',
                        metavar='rfq_id',
                        type=str,
                        help='RFQ Id',
                        default="-1",
                        nargs='?')
    my_parser.add_argument('CLIENT_ORDER_ID',
                        metavar='client_order_id',
                        type=str,
                        help='Client Order Id',
                        default="-1",
                        nargs='?')
    my_parser.add_argument('PAGE',
                        metavar='page',
                        type=str,
                        help='Page Number of returned results',
                        default="-1",
                        nargs='?')
    my_parser.add_argument('STATUS',
                        metavar='status',
                        type=str,
                        help='Status of RFQ ACTIVE|CANCELED',
                        default="-1",
                        nargs='?')
    
    my_parser.add_argument('ACCESS_KEY',
                        metavar='api_key',
                        type=str,
                        help='Paradigm Account Access Key',
                        default='kNLMKQnbcM0xGSL2wOntLwpy',
                        nargs='?')
    my_parser.add_argument('SECRET_KEY',
                        metavar='secret_key',
                        type=str,
                        help='Paradigm Account Secret Key',
                        default='8Ni+xM1Y8DJTvCw0e0Wv0623KStavy1tBzLP3Wh7dryMWwkj',
                        nargs='?')

    args = my_parser.parse_args()

    rfq_id = args.RFQ_ID
    client_order_id = args.CLIENT_ORDER_ID
    page = args.PAGE
    status = args.STATUS

    access_key = args.ACCESS_KEY
    signing_key = base64.b64decode(args.SECRET_KEY)

    # Local Testing
    # "-1" if unused
    rfq_id = "-1"
    client_order_id = "-1"
    page = "-1"
    status = "-1"

    access_key = '<access-key>'
    signing_key = base64.b64decode('<secret-key>')

    print('RFQ Id: {}'.format(rfq_id))
    print('Client Order Id: {}'.format(client_order_id))
    print('Page: {}'.format(page))
    print('Status: {}'.format(status))
    print()
    print('Paradigm Account Access Key: {}'.format(access_key))
    print('Paradigm Account Secret Key: {}'.format(signing_key))

    ParadigmRestClient(rfq_id=rfq_id,
                       client_order_id=client_order_id,
                       page=page,
                       status=status,
                       access_key=access_key,
                       secret_key=signing_key).get_rfq()
