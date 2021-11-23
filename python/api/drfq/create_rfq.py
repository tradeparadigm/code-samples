#!/usr/bin/env python3
"""
Paradigm REST over HTTP script that allows you to create an RFQ.

Run the script and provide the arguements for instruments, directions,
quantities, counterparties, and disclosure basis.

Usage:
    python3 create_rfq.py --help

Requirements:
    pip3 install click
    pip3 install click-log
    pip3 install requests
"""

import base64
import hmac
import json
import logging
import time
import uuid
from typing import List, NamedTuple
from urllib.parse import urljoin

import click
import click_log
import requests


logger = logging.getLogger(__name__)
click_log.basic_config(logger)


class RFQLeg(NamedTuple):
    side: str
    instrument: str
    quantity: float
    venue: str


class ParadigmRestClient():
    def __init__(self, host: str, access_key: str = None,
                 secret_key: str = None, account_name: str = None,
                 counterparties: List[str] = None, expires_in: int = None,
                 legs: List[RFQLeg] = None, anonymous: bool = None):
        # User Credentials
        self.access_key = access_key
        self.signing_key = secret_key

        # RFQ Account Information
        self.account_name = account_name
        self.counterparties = counterparties
        self.expires_in = expires_in

        # RFQ Leg Information
        self.legs = legs

        # Other RFQ Metadata
        self.is_anonymous = anonymous

        # Initlize Requests Session
        self.host = host
        self.session = requests.Session()

    def request(self, action=None, data=None, method=None):

        # Generate Signature
        signature, timestamp = self.generate_signature(action=action,
                                                       data=data,
                                                       method=method)

        # HTTP Request Headers
        headers = {
            'Paradigm-API-Timestamp': timestamp,
            'Paradigm-API-Signature': signature,
            'Authorization': f'Bearer {self.access_key}'
        }

        # POST Request
        return requests.post(urljoin(self.host, action),
                             headers=headers,
                             json=data)

    def generate_signature(self, action, data, method):
        json_payload = json.dumps(data).encode('utf-8')

        message = method.encode('utf-8') + b'\n'
        message += action.encode('utf-8') + b'\n'
        message += json_payload

        timestamp = str(int(time.time() * 1000))
        message = timestamp.encode('utf-8') + b'\n' + message
        digest = hmac.digest(self.signing_key, message, 'sha256')
        signature = base64.b64encode(digest)

        return signature, timestamp

    def rfq_create(self):
        # Random Client Order
        client_order_id = str(uuid.uuid4())

        legs = []
        for leg in self.legs:
            legs.append({
                'quantity': leg.quantity,
                'side': leg.side.upper(),
                'instrument': leg.instrument.upper(),
                'venue': leg.venue.upper(),
            })

        payload = {
            'account': {
                'name': self.account_name
            },
            'client_order_id': client_order_id,
            'anonymous': self.is_anonymous,
            'counterparties': self.counterparties,
            'expires_in': self.expires_in,
            'legs': legs,
        }

        response = self.request(action='/rfq/create/', data=payload, method='POST')

        # Check response code for error
        if response.status_code != 200 and response.status_code != 201:
            logger.error('Incorrect response code: %s', response.status_code)
            logger.error('Response body: %s', response.text)
        else:
            logger.info('RFQ Created Successfully!')
        return response


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click_log.simple_verbosity_option(logger)
@click.option('--access-key',
              help='Paradigm Account API Access Key.',
              metavar='ACCESS_KEY', prompt=True)
@click.option('--secret-key',
              help='Paradigm Account API Secret Key.',
              metavar='SECRET_KEY', prompt=True, hide_input=True)
@click.option('--account-name',
              help='Name of your Paradigm Account you would like to RFQ from.',
              metavar='ACCOUNT', required=True)
@click.option('--counterparty', '-c', 'counterparties',
              help=' '.join([
                'Counterparty Ticker (e.g. DSK1).',
                'May be repeated to specify multiple counterparties.',
              ]),
              metavar='TICKER', multiple=True, required=True)
@click.option('--expires-in',
              help='RFQ Expiry in seconds.',
              type=int, required=True)
@click.option('--leg', 'legs',
              help=' '.join([
                'Leg data as space-separated fields.',
                'Direction can be BUY or SELL.',
                'May be repeated to specify multiple legs.',
              ]),
              metavar='DIRECTION INSTRUMENT QUANTITY VENUE',
              type=(str, str, float, str), multiple=True)
@click.option('--anonymous/--no-anonymous',
              help='Disclosed or Anonymous RFQ.',
              default=False, show_default=True)
@click.option('--host',
              help='The Paradigm API host to send the RFQ to.',
              metavar='HOST', default='https://api.test.paradigm.co',
              show_default=True)
def create_rfq(access_key, secret_key, account_name, counterparties,
               expires_in, legs, anonymous, host):
    """
    Paradigm REST over HTTP script that allows you to create an RFQ.

    Run the script and provide the arguements for instruments,
    directions, quantities, counterparties, and disclosure basis.
    """

    signing_key = base64.b64decode(secret_key)
    legs = [RFQLeg(*leg) for leg in legs]

    logger.info('Paradigm Account Name: %s', account_name)
    logger.info('Counterparties: %s', ','.join(counterparties))
    logger.info('RFQ Expires In: %d', expires_in)
    logger.info('Anonymous: %s', anonymous)

    for i, leg in enumerate(legs, start=1):
        logger.info('Leg %d:', i)
        logger.info('=> Direction: %s', leg.side)
        logger.info('=> Instrument: %s', leg.instrument)
        logger.info('=> Quantity: %s', leg.quantity)
        logger.info('=> Venue: %s', leg.venue)

    client = ParadigmRestClient(
        host=host, account_name=account_name,
        counterparties=counterparties, expires_in=expires_in, legs=legs,
        anonymous=anonymous, access_key=access_key, secret_key=signing_key)
    client.rfq_create()


if __name__ == "__main__":
    create_rfq()
