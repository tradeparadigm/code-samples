"""
Paradigm REST over HTTP script that allows you to create an RFQ.

Run the script and provide the arguements for instruments, directions,
quantities, counterparties, and disclosure basis.

Usage:
    python3 create_rfq.py [PARADIGM_ACCOUNT_NAME] [COUNTERPARTIES] [EXPIRES_IN]
                          [DIRECTION_1] [INSTRUMENT_1] [INSTRUMENT_QUANTITY_1] [VENUE_1]
                          [DIRECTION_2] [INSTRUMENT_2] [INSTRUMENT_QUANTITY_2] [VENUE_2]
                          [DIRECTION_3] [INSTRUMENT_3] [INSTRUMENT_QUANTITY_3] [VENUE_3]
                          [DIRECTION_4] [INSTRUMENT_4] [INSTRUMENT_QUANTITY_4] [VENUE_4]
                          [DIRECTION_5] [INSTRUMENT_5] [INSTRUMENT_QUANTITY_5] [VENUE_5]
                          [DIRECTION_6] [INSTRUMENT_6] [INSTRUMENT_QUANTITY_6] [VENUE_6]
                          [ANONYMOUS] [ACCESS KEY] [SECRET KEY]

Requirements:
    pip3 install requests
"""

import argparse
import base64
import hmac
import json
import requests
import time

from random import randint
from urllib.parse import urljoin


class ParadigmRestClient():
    def __init__(self, access_key=None, secret_key=None, host=None,
                    paradigm_account_name=None, counterparties=None, expires_in=None,
                    rfq_direction_one=None, rfq_instrument_one=None, rfq_instrument_quantity_one=None, rfq_venue_one=None,
                    rfq_direction_two=None, rfq_instrument_two=None, rfq_instrument_quantity_two=None, rfq_venue_two=None,
                    rfq_direction_three=None, rfq_instrument_three=None, rfq_instrument_quantity_three=None, rfq_venue_three=None,
                    rfq_direction_four=None, rfq_instrument_four=None, rfq_instrument_quantity_four=None, rfq_venue_four=None,
                    rfq_direction_five=None, rfq_instrument_five=None, rfq_instrument_quantity_five=None, rfq_venue_five=None,
                    rfq_direction_six=None, rfq_instrument_six=None, rfq_instrument_quantity_six=None, rfq_venue_six=None,
                    anonymous_flag=None):
        # User Credentials
        self.access_key = access_key
        self.signing_key = secret_key

        # RFQ Account Information
        self.paradigm_account_name = paradigm_account_name
        self.counterparties = list(map(str, counterparties.strip('[]').split(',')))
        self.expires_in = expires_in

        # RFQ Leg Information
        self.rfq_direction_one = rfq_direction_one
        self.rfq_instrument_one = rfq_instrument_one
        self.rfq_instrument_quantity_one = rfq_instrument_quantity_one
        self.rfq_venue_one = rfq_venue_one

        self.rfq_direction_two = rfq_direction_two
        self.rfq_instrument_two = rfq_instrument_two
        self.rfq_instrument_quantity_two = rfq_instrument_quantity_two
        self.rfq_venue_two = rfq_venue_two

        self.rfq_direction_three = rfq_direction_three
        self.rfq_instrument_three = rfq_instrument_three
        self.rfq_instrument_quantity_three = rfq_instrument_quantity_three
        self.rfq_venue_three = rfq_venue_three

        self.rfq_direction_four = rfq_direction_four
        self.rfq_instrument_four = rfq_instrument_four
        self.rfq_instrument_quantity_four = rfq_instrument_quantity_four
        self.rfq_venue_four = rfq_venue_four

        self.rfq_direction_five = rfq_direction_five
        self.rfq_instrument_five = rfq_instrument_five
        self.rfq_instrument_quantity_five = rfq_instrument_quantity_five
        self.rfq_venue_five = rfq_venue_five

        self.rfq_direction_six = rfq_direction_six
        self.rfq_instrument_six = rfq_instrument_six
        self.rfq_instrument_quantity_six = rfq_instrument_quantity_six
        self.rfq_venue_six = rfq_venue_six

        self.anonymous_flag = anonymous_flag

        # Determine number of legs being traded
        self.legs_traded_count = 0
        for leg in [self.rfq_instrument_quantity_one, self.rfq_instrument_quantity_two,
                    self.rfq_instrument_quantity_three, self.rfq_instrument_quantity_four,
                    self.rfq_instrument_quantity_five, self.rfq_instrument_quantity_six]:
            self.legs_traded_count += 1 if leg > 0 else 0

        # Initlize Requests Session
        self.session = requests.Session()

        if host:
            self.host = host
        else:
            self.host = 'https://api.nightly.paradigm.co'

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
        response = requests.post(urljoin(self.host, action),
                                    headers=headers,
                                    json=data)

        # Check response code for error
        if response.status_code != 200 and response.status_code != 201:
            print('Incorrect response code: {0}'.format(response.status_code))
            print('Response Text: {}'.format(response.text))
            # print('Quote Provided:')
            # print(json.dumps(data))

        # print(response.status_code)
        # print(response.text)
        print(json.dumps(data))

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
        client_order_id_random = randint(1, 1000000000)
        # print('Client_Order_Id: {}'.format(client_order_id_random))

        # RFQ to Send
        if self.legs_traded_count == 1:
            payload = {
                        "account": {
                                    "name": self.paradigm_account_name
                                    },
                        "client_order_id": client_order_id_random,
                        "anonymous": self.anonymous_flag,
                        "counterparties": self.counterparties,
                        "expires_in": self.expires_in,
                        "legs": [
                                {
                                "quantity": self.rfq_instrument_quantity_one,
                                "side": self.rfq_direction_one,
                                "instrument": self.rfq_instrument_one,
                                "venue": self.rfq_venue_one
                                }
                                ]
                        }
        elif self.legs_traded_count == 2:
            payload = {
                        "account": {
                                    "name": self.paradigm_account_name
                                    },
                        "client_order_id": client_order_id_random,
                        "anonymous": self.anonymous_flag,
                        "counterparties": self.counterparties,
                        "expires_in": self.expires_in,
                        "legs": [
                                {
                                "quantity": self.rfq_instrument_quantity_one,
                                "side": self.rfq_direction_one,
                                "instrument": self.rfq_instrument_one,
                                "venue": self.rfq_venue_one
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_two,
                                "side": self.rfq_direction_two,
                                "instrument": self.rfq_instrument_two,
                                "venue": self.rfq_venue_two
                                }
                                ]
                        }
        elif self.legs_traded_count == 3:
            payload = {
                        "account": {
                                    "name": self.paradigm_account_name
                                    },
                        "client_order_id": client_order_id_random,
                        "anonymous": self.anonymous_flag,
                        "counterparties": self.counterparties,
                        "expires_in": self.expires_in,
                        "legs": [
                                {
                                "quantity": self.rfq_instrument_quantity_one,
                                "side": self.rfq_direction_one,
                                "instrument": self.rfq_instrument_one,
                                "venue": self.rfq_venue_one
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_two,
                                "side": self.rfq_direction_two,
                                "instrument": self.rfq_instrument_two,
                                "venue": self.rfq_venue_two
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_three,
                                "side": self.rfq_direction_three,
                                "instrument": self.rfq_instrument_three,
                                "venue": self.rfq_venue_three
                                }
                                ]
                        }
        elif self.legs_traded_count == 4:
            payload = {
                        "account": {
                                    "name": self.paradigm_account_name
                                    },
                        "client_order_id": client_order_id_random,
                        "anonymous": self.anonymous_flag,
                        "counterparties": self.counterparties,
                        "expires_in": self.expires_in,
                        "legs": [
                                {
                                "quantity": self.rfq_instrument_quantity_one,
                                "side": self.rfq_direction_one,
                                "instrument": self.rfq_instrument_one,
                                "venue": self.rfq_venue_one
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_two,
                                "side": self.rfq_direction_two,
                                "instrument": self.rfq_instrument_two,
                                "venue": self.rfq_venue_two
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_three,
                                "side": self.rfq_direction_three,
                                "instrument": self.rfq_instrument_three,
                                "venue": self.rfq_venue_three
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_four,
                                "side": self.rfq_direction_four,
                                "instrument": self.rfq_instrument_four,
                                "venue": self.rfq_venue_four
                                }
                                ]
                        }
        elif self.legs_traded_count == 5:
            payload = {
                        "account": {
                                    "name": self.paradigm_account_name
                                    },
                        "client_order_id": client_order_id_random,
                        "anonymous": self.anonymous_flag,
                        "counterparties": self.counterparties,
                        "expires_in": self.expires_in,
                        "legs": [
                                {
                                "quantity": self.rfq_instrument_quantity_one,
                                "side": self.rfq_direction_one,
                                "instrument": self.rfq_instrument_one,
                                "venue": self.rfq_venue_one
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_two,
                                "side": self.rfq_direction_two,
                                "instrument": self.rfq_instrument_two,
                                "venue": self.rfq_venue_two
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_three,
                                "side": self.rfq_direction_three,
                                "instrument": self.rfq_instrument_three,
                                "venue": self.rfq_venue_three
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_four,
                                "side": self.rfq_direction_four,
                                "instrument": self.rfq_instrument_four,
                                "venue": self.rfq_venue_four
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_five,
                                "side": self.rfq_direction_five,
                                "instrument": self.rfq_instrument_five,
                                "venue": self.rfq_venue_five
                                }
                                ]
                        }
        elif self.legs_traded_count == 6:
            payload = {
                        "account": {
                                    "name": self.paradigm_account_name
                                    },
                        "client_order_id": client_order_id_random,
                        "anonymous": self.anonymous_flag,
                        "counterparties": self.counterparties,
                        "expires_in": self.expires_in,
                        "legs": [
                                {
                                "quantity": self.rfq_instrument_quantity_one,
                                "side": self.rfq_direction_one,
                                "instrument": self.rfq_instrument_one,
                                "venue": self.rfq_venue_one
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_two,
                                "side": self.rfq_direction_two,
                                "instrument": self.rfq_instrument_two,
                                "venue": self.rfq_venue_two
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_three,
                                "side": self.rfq_direction_three,
                                "instrument": self.rfq_instrument_three,
                                "venue": self.rfq_venue_three
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_four,
                                "side": self.rfq_direction_four,
                                "instrument": self.rfq_instrument_four,
                                "venue": self.rfq_venue_four
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_five,
                                "side": self.rfq_direction_five,
                                "instrument": self.rfq_instrument_five,
                                "venue": self.rfq_venue_five
                                },
                                {
                                "quantity": self.rfq_instrument_quantity_six,
                                "side": self.rfq_direction_six,
                                "instrument": self.rfq_instrument_six,
                                "venue": self.rfq_venue_six
                                }
                                ]
                        }

        return self.request(action='/rfq/create/', data=payload, method='POST')


if __name__ == "__main__":
    # Arguments
    my_parser = argparse.ArgumentParser()

    my_parser.add_argument('PARADIGM_ACCOUNT_NAME',
                        metavar='paradigm_account_name',
                        type=str,
                        help='Name of your Paradigm Account you would like to RFQ from',
                        default='',
                        nargs='?')
    my_parser.add_argument('COUNTERPARTIES',
                        metavar='paradigm_account_name',
                        type=str,
                        help='String List of Counterparties [DSK1, DSK2]',
                        default='',
                        nargs='?')
    my_parser.add_argument('EXPIRES_IN',
                        metavar='EXPIRES_IN',
                        type=int,
                        help='RFQ Expiry in Seconds INT',
                        default=0,
                        nargs='?')

    my_parser.add_argument('DIRECTION_1',
                        metavar='direction_1',
                        type=str,
                        help='Direction of the first leg BUY|SELL',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_1',
                        metavar='instrument_1',
                        type=str,
                        help='First Instrument Name',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_QUANTITY_1',
                        metavar='instrument_quantity_1',
                        type=float,
                        help='First Instrument Quantity',
                        default=0,
                        nargs='?')
    my_parser.add_argument('VENUE_1',
                        metavar='VENUE_1',
                        type=str,
                        help='First Instrument Venue',
                        default='',
                        nargs='?')

    my_parser.add_argument('DIRECTION_2',
                        metavar='direction_2',
                        type=str,
                        help='Direction of the second leg BUY|SELL',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_2',
                        metavar='instrument_2',
                        type=str,
                        help='Second Instrument Name',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_QUANTITY_2',
                        metavar='instrument_quantity_2',
                        type=float,
                        help='Second Instrument Quantity',
                        default=0,
                        nargs='?')
    my_parser.add_argument('VENUE_2',
                        metavar='venue_2',
                        type=str,
                        help='Second Instrument Venue',
                        default='',
                        nargs='?')

    my_parser.add_argument('DIRECTION_3',
                        metavar='direction_3',
                        type=str,
                        help='Direction of the third leg BUY|SELL',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_3',
                        metavar='instrument_3',
                        type=str,
                        help='Third Instrument Name',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_QUANTITY_3',
                        metavar='instrument_quantity_3',
                        type=float,
                        help='Third Instrument Quantity',
                        default=0,
                        nargs='?')
    my_parser.add_argument('VENUE_3',
                        metavar='venue_2',
                        type=str,
                        help='Third Instrument Venue',
                        default='',
                        nargs='?')

    my_parser.add_argument('DIRECTION_4',
                        metavar='direction_4',
                        type=str,
                        help='Direction of the fourth leg BUY|SELL',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_4',
                        metavar='instrument_4',
                        type=str,
                        help='Fourth Instrument Name',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_QUANTITY_4',
                        metavar='instrument_quantity_4',
                        type=float,
                        help='Fourth Instrument Quantity',
                        default=0,
                        nargs='?')
    my_parser.add_argument('VENUE_4',
                        metavar='venue_4',
                        type=str,
                        help='Fourth Instrument Venue',
                        default='',
                        nargs='?')

    my_parser.add_argument('DIRECTION_5',
                        metavar='direction_5',
                        type=str,
                        help='Direction of the fifth leg BUY|SELL',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_5',
                        metavar='instrument_5',
                        type=str,
                        help='Fifth Instrument Name',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_QUANTITY_5',
                        metavar='instrument_quantity_5',
                        type=float,
                        help='Fifth Instrument Quantity',
                        default=0,
                        nargs='?')
    my_parser.add_argument('VENUE_5',
                        metavar='venue_5',
                        type=str,
                        help='Fifth Instrument Venue',
                        default='',
                        nargs='?')

    my_parser.add_argument('DIRECTION_6',
                        metavar='direction_6',
                        type=str,
                        help='Direction of the sixth leg BUY|SELL',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_6',
                        metavar='instrument_6',
                        type=str,
                        help='Sixth Instrument Name',
                        default='',
                        nargs='?')
    my_parser.add_argument('INSTRUMENT_QUANTITY_6',
                        metavar='instrument_quantity_6',
                        type=float,
                        help='Sixth Instrument Quantity',
                        default=0,
                        nargs='?')
    my_parser.add_argument('VENUE_6',
                        metavar='venue_6',
                        type=str,
                        help='Sixth Instrument Venue',
                        default='',
                        nargs='?')

    my_parser.add_argument('ANONYMOUS',
                        metavar='anonymous',
                        type=bool,
                        help='Disclosed or Anonymous RFQ True|False',
                        default=False,
                        nargs='?')

    my_parser.add_argument('ACCESS_KEY',
                        metavar='api_key',
                        type=str,
                        help='Paradigm Account Access Key',
                        default='',
                        nargs='?')
    my_parser.add_argument('SECRET_KEY',
                        metavar='secret_key',
                        type=str,
                        help='Paradigm Account Secret Key',
                        default='',
                        nargs='?')

    args = my_parser.parse_args()

    paradigm_account_name = args.PARADIGM_ACCOUNT_NAME
    counterparties = args.COUNTERPARTIES
    expires_in = args.EXPIRES_IN

    direction_one = args.DIRECTION_1
    instrument_one = args.INSTRUMENT_1
    instrument_quantity_one = args.INSTRUMENT_QUANTITY_1
    venue_one = args.VENUE_1

    direction_two = args.DIRECTION_2
    instrument_two = args.INSTRUMENT_2
    instrument_quantity_two = args.INSTRUMENT_QUANTITY_2
    venue_two = args.VENUE_2

    direction_three = args.DIRECTION_3
    instrument_three = args.INSTRUMENT_3
    instrument_quantity_three = args.INSTRUMENT_QUANTITY_3
    venue_three = args.VENUE_3

    direction_four = args.DIRECTION_4
    instrument_four = args.INSTRUMENT_4
    instrument_quantity_four = args.INSTRUMENT_QUANTITY_4
    venue_four = args.VENUE_4

    direction_five = args.DIRECTION_5
    instrument_five = args.INSTRUMENT_5
    instrument_quantity_five = args.INSTRUMENT_QUANTITY_5
    venue_five = args.VENUE_5

    direction_six = args.DIRECTION_6
    instrument_six = args.INSTRUMENT_6
    instrument_quantity_six = args.INSTRUMENT_QUANTITY_6
    venue_six = args.VENUE_6

    anonymous_flag = args.ANONYMOUS

    access_key = args.ACCESS_KEY
    signing_key = base64.b64decode(args.SECRET_KEY)

    # Local Testing

    # Scenario 1 == DBT - 1 BTC-PERP
    # Scenario 2 == DBT - 1 PERP / 1 Future
    # Scenario 3 == DBT - 1 Option
    # Scenario 4 == DBT - 2 Option
    # Scenario 5 == DBT - 6 Options
    # Scenario 6 == BIT - 1 PERP
    # Scenario 7 == BIT - 1 PERP / 1 Future
    # Scenario 8 == BIT - 1 Option
    # Scenario 9 == BIT - 2 Options
    # Scenario 10 == BIT - 6 Options
    scenario = 6
    for scenario in range(1, 11):
        if scenario == 1:
            expires_in = 60

            direction_one = "BUY"
            instrument_one = "BTC-PERPETUAL"
            instrument_quantity_one = 20000
            venue_one = "DBT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 2:
            expires_in = 120

            direction_one = "SELL"
            instrument_one = "BTC-PERPETUAL"
            instrument_quantity_one = 10000
            venue_one = "DBT"

            direction_two = "BUY"
            instrument_two = "BTC-25DEC20"
            instrument_quantity_two = 10000
            venue_two = "DBT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Leg 2 - Direction: {}'.format(direction_two))
            print('RFQ Leg 2 - Instrument Name: {}'.format(instrument_two))
            print('RFQ Leg 2 - Instrument Quantity: {}'.format(instrument_quantity_two))
            print('RFQ Leg 2 - Venue: {}'.format(venue_two))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 3:
            instrument_quantity_two = 0

            expires_in = 120

            direction_one = "BUY"
            instrument_one = "BTC-25DEC20-18000-C"
            instrument_quantity_one = 50
            venue_one = "DBT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 4:
            expires_in = 120

            direction_one = "BUY"
            instrument_one = "BTC-25DEC20-18000-C"
            instrument_quantity_one = 25
            venue_one = "DBT"

            direction_two = "BUY"
            instrument_two = "BTC-29JAN21-18000-C"
            instrument_quantity_two = 25
            venue_two = "DBT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Leg 2 - Direction: {}'.format(direction_two))
            print('RFQ Leg 2 - Instrument Name: {}'.format(instrument_two))
            print('RFQ Leg 2 - Instrument Quantity: {}'.format(instrument_quantity_two))
            print('RFQ Leg 2 - Venue: {}'.format(venue_two))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 5:
            expires_in = 120

            direction_one = "BUY"
            instrument_one = "BTC-25DEC20-18000-C"
            instrument_quantity_one = 5
            venue_one = "DBT"

            direction_two = "BUY"
            instrument_two = "BTC-29JAN21-18000-C"
            instrument_quantity_two = 5
            venue_two = "DBT"

            direction_three = "BUY"
            instrument_three = "BTC-25DEC20-17000-P"
            instrument_quantity_three = 5
            venue_three = "DBT"

            direction_four = "SELL"
            instrument_four = "BTC-29JAN21-16000-P"
            instrument_quantity_four = 5
            venue_four = "DBT"

            direction_five = "SELL"
            instrument_five = "BTC-29JAN21-16000-C"
            instrument_quantity_five = 5
            venue_five = "DBT"

            direction_six = "SELL"
            instrument_six = "BTC-25DEC20-15000-C"
            instrument_quantity_six = 5
            venue_six = "DBT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Leg 2 - Direction: {}'.format(direction_two))
            print('RFQ Leg 2 - Instrument Name: {}'.format(instrument_two))
            print('RFQ Leg 2 - Instrument Quantity: {}'.format(instrument_quantity_two))
            print('RFQ Leg 2 - Venue: {}'.format(venue_two))
            print()
            print('RFQ Leg 3 - Direction: {}'.format(direction_three))
            print('RFQ Leg 3 - Instrument Name: {}'.format(instrument_three))
            print('RFQ Leg 3 - Instrument Quantity: {}'.format(instrument_quantity_three))
            print('RFQ Leg 3 - Venue: {}'.format(venue_three))
            print()
            print('RFQ Leg 4 - Direction: {}'.format(direction_four))
            print('RFQ Leg 4 - Instrument Name: {}'.format(instrument_four))
            print('RFQ Leg 4 - Instrument Quantity: {}'.format(instrument_quantity_four))
            print('RFQ Leg 4 - Venue: {}'.format(venue_four))
            print()
            print('RFQ Leg 5 - Direction: {}'.format(direction_five))
            print('RFQ Leg 5 - Instrument Name: {}'.format(instrument_five))
            print('RFQ Leg 5 - Instrument Quantity: {}'.format(instrument_quantity_five))
            print('RFQ Leg 5 - Venue: {}'.format(venue_five))
            print()
            print('RFQ Leg 6 - Direction: {}'.format(direction_six))
            print('RFQ Leg 6 - Instrument Name: {}'.format(instrument_six))
            print('RFQ Leg 6 - Instrument Quantity: {}'.format(instrument_quantity_six))
            print('RFQ Leg 6 - Venue: {}'.format(venue_six))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 6:
            # set old variables to None
            direction_one = None
            instrument_one = None
            instrument_quantity_one = 0
            venue_one = None

            direction_two = None
            instrument_two = None
            instrument_quantity_two = 0
            venue_two = None

            direction_three = None
            instrument_three = None
            instrument_quantity_three = 0
            venue_three = None

            direction_four = None
            instrument_four = None
            instrument_quantity_four = 0
            venue_four = None

            direction_five = None
            instrument_five = None
            instrument_quantity_five = 0
            venue_five = None

            direction_six = None
            instrument_six = None
            instrument_quantity_six = 0
            venue_six = None

            expires_in = 75

            direction_one = "BUY"
            instrument_one = "BTC-PERPETUAL"
            instrument_quantity_one = 20000
            venue_one = "BIT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 7:
            expires_in = 60

            direction_one = "BUY"
            instrument_one = "BTC-PERPETUAL"
            instrument_quantity_one = 10000
            venue_one = "BIT"

            direction_two = "SELL"
            instrument_two = "BTC-25DEC20-F"
            instrument_quantity_two = 10000
            venue_two = "BIT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Leg 2 - Direction: {}'.format(direction_two))
            print('RFQ Leg 2 - Instrument Name: {}'.format(instrument_two))
            print('RFQ Leg 2 - Instrument Quantity: {}'.format(instrument_quantity_two))
            print('RFQ Leg 2 - Venue: {}'.format(venue_two))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 8:
            expires_in = 60

            direction_one = "BUY"
            instrument_one = "BTC-25DEC20-18000-C"
            instrument_quantity_one = 25
            venue_one = "BIT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 9:
            expires_in = 60

            direction_one = "BUY"
            instrument_one = "BTC-25DEC20-18000-C"
            instrument_quantity_one = 13
            venue_one = "BIT"

            direction_two = "SELL"
            instrument_two = "BTC-29JAN21-18000-C"
            instrument_quantity_two = 13
            venue_two = "BIT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Leg 2 - Direction: {}'.format(direction_two))
            print('RFQ Leg 2 - Instrument Name: {}'.format(instrument_two))
            print('RFQ Leg 2 - Instrument Quantity: {}'.format(instrument_quantity_two))
            print('RFQ Leg 2 - Venue: {}'.format(venue_two))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()
        elif scenario == 10:
            expires_in = 60

            direction_one = "BUY"
            instrument_one = "BTC-25DEC20-18000-C"
            instrument_quantity_one = 5
            venue_one = "BIT"

            direction_two = "BUY"
            instrument_two = "BTC-29JAN21-18000-C"
            instrument_quantity_two = 5
            venue_two = "BIT"

            direction_three = "BUY"
            instrument_three = "BTC-25DEC20-17000-P"
            instrument_quantity_three = 5
            venue_three = "BIT"

            direction_four = "SELL"
            instrument_four = "BTC-29JAN21-16000-P"
            instrument_quantity_four = 5
            venue_four = "BIT"

            direction_five = "SELL"
            instrument_five = "BTC-29JAN21-16000-C"
            instrument_quantity_five = 5
            venue_five = "BIT"

            direction_six = "SELL"
            instrument_six = "BTC-25DEC20-15000-C"
            instrument_quantity_six = 5
            venue_six = "BIT"

            anonymous_flag = False

            print('RFQ Leg 1 - Direction: {}'.format(direction_one))
            print('RFQ Leg 1 - Instrument Name: {}'.format(instrument_one))
            print('RFQ Leg 1 - Instrument Quantity: {}'.format(instrument_quantity_one))
            print('RFQ Leg 1 - Venue: {}'.format(venue_one))
            print()
            print('RFQ Leg 2 - Direction: {}'.format(direction_two))
            print('RFQ Leg 2 - Instrument Name: {}'.format(instrument_two))
            print('RFQ Leg 2 - Instrument Quantity: {}'.format(instrument_quantity_two))
            print('RFQ Leg 2 - Venue: {}'.format(venue_two))
            print()
            print('RFQ Leg 3 - Direction: {}'.format(direction_three))
            print('RFQ Leg 3 - Instrument Name: {}'.format(instrument_three))
            print('RFQ Leg 3 - Instrument Quantity: {}'.format(instrument_quantity_three))
            print('RFQ Leg 3 - Venue: {}'.format(venue_three))
            print()
            print('RFQ Leg 4 - Direction: {}'.format(direction_four))
            print('RFQ Leg 4 - Instrument Name: {}'.format(instrument_four))
            print('RFQ Leg 4 - Instrument Quantity: {}'.format(instrument_quantity_four))
            print('RFQ Leg 4 - Venue: {}'.format(venue_four))
            print()
            print('RFQ Leg 5 - Direction: {}'.format(direction_five))
            print('RFQ Leg 5 - Instrument Name: {}'.format(instrument_five))
            print('RFQ Leg 5 - Instrument Quantity: {}'.format(instrument_quantity_five))
            print('RFQ Leg 5 - Venue: {}'.format(venue_five))
            print()
            print('RFQ Leg 6 - Direction: {}'.format(direction_six))
            print('RFQ Leg 6 - Instrument Name: {}'.format(instrument_six))
            print('RFQ Leg 6 - Instrument Quantity: {}'.format(instrument_quantity_six))
            print('RFQ Leg 6 - Venue: {}'.format(venue_six))
            print()
            print('RFQ Anonymous: {}'.format(anonymous_flag))
            print()

        paradigm_account_name = 'ParadigmTestOne'
        counterparties = '[DSK2, DSK3, DSK4, DSK5, MSTL1]'

        print('Paradigm Account Name: {}'.format(paradigm_account_name))
        print('Paradigm Account Access Key: {}'.format(access_key))
        print('Paradigm Account Secret Key: {}'.format(signing_key))
        print('RFQ Countparties: {}'.format(counterparties))
        print('RFQ Expires In: {}'.format(expires_in))

        ParadigmRestClient(paradigm_account_name=paradigm_account_name,
                        counterparties=counterparties,
                        expires_in=expires_in,
                        rfq_direction_one=direction_one,
                        rfq_instrument_one=instrument_one,
                        rfq_instrument_quantity_one=instrument_quantity_one,
                        rfq_venue_one=venue_one,
                        rfq_direction_two=direction_two,
                        rfq_instrument_two=instrument_two,
                        rfq_instrument_quantity_two=instrument_quantity_two,
                        rfq_venue_two=venue_two,
                        rfq_direction_three=direction_three,
                        rfq_instrument_three=instrument_three,
                        rfq_instrument_quantity_three=instrument_quantity_three,
                        rfq_venue_three=venue_three,
                        rfq_direction_four=direction_four,
                        rfq_instrument_four=instrument_four,
                        rfq_instrument_quantity_four=instrument_quantity_four,
                        rfq_venue_four=venue_four,
                        rfq_direction_five=direction_five,
                        rfq_instrument_five=instrument_five,
                        rfq_instrument_quantity_five=instrument_quantity_five,
                        rfq_venue_five=venue_five,
                        rfq_direction_six=direction_six,
                        rfq_instrument_six=instrument_six,
                        rfq_instrument_quantity_six=instrument_quantity_six,
                        rfq_venue_six=venue_five,
                        anonymous_flag=anonymous_flag,
                        access_key=access_key,
                        secret_key=signing_key).rfq_create()

