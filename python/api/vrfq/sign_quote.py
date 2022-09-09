import os
import time
from decimal import Decimal
from enum import Enum

import click
from paradigm_api import ParadigmClient, ParadigmCredential
from ribbon_api import sign_ribbon_bid


def _get_value_from_env(key: str, default=None):
    value = os.getenv(key, default=default)

    if not value:
        raise ValueError(f"Must provide a value for {key}")

    return value


class Venue(str, Enum):
    RIBBON = 'ribbon'


@click.command()
@click.argument('venue', type=click.Choice(Venue))
@click.option('--rfq_id', type=int, required=True)
@click.option('--price', required=True)
@click.option('--wallet_name', required=True)
def main(venue: Venue, rfq_id: int, price: str, wallet_name: str, seconds: int = 5):

    ###########################
    # SETUP

    host = _get_value_from_env('PARADIGM_API_HOST', default='https://api.test.paradigm.co')
    access_key = _get_value_from_env('PARADIGM_ACCESS_KEY')
    secret_key = _get_value_from_env('PARADIGM_SECRET_KEY')

    paradigm_credential = ParadigmCredential(access_key=access_key, secret_key=secret_key)
    paradigm_client = ParadigmClient(credential=paradigm_credential, host=host)

    if venue == Venue.RIBBON:
        sign_fn = sign_ribbon_bid
        wallet_private_key = _get_value_from_env('EVM_WALLET_PRIVATE_KEY')
        use_nonce = True
    else:
        raise NotImplementedError(f'Bid signing not implemented for venue {venue}')

    price = Decimal(price)

    ###########################
    # FLOW

    # Get data (listen to websockets otherwise)
    rfq_data = paradigm_client.get_rfq_data(rfq_id)

    # True if using multi signature
    use_delegated_wallet = False

    # Get the valid format of payload to sign
    bidding_data = paradigm_client.get_bidding_data(
        rfq_id, price, wallet_name, use_nonce=use_nonce, use_delegated_wallet=use_delegated_wallet
    )

    # Build signature
    bidding_data['signature'] = sign_fn(
        rfq_data, bidding_data, wallet_private_key=wallet_private_key
    )

    # Create quote
    response = paradigm_client.place_bid(rfq_id, price, wallet_name, bidding_data)
    print(f"Bid response:\n{response}")

    # Cancel latest quote
    if quote_id := response.get('id'):
        print(f"Removing in {seconds} seconds")
        time.sleep(seconds)
        response = paradigm_client.remove_bid(quote_id)
        print(f"Removing response:\n{response}")


if __name__ == '__main__':
    main()
