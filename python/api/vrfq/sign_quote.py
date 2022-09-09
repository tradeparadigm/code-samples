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
    host = _get_value_from_env('PARADIGM_API_HOST', default='https://api.test.paradigm.co')
    access_key = _get_value_from_env('PARADIGM_ACCESS_KEY')
    secret_key = _get_value_from_env('PARADIGM_SECRET_KEY')

    paradigm_credential = ParadigmCredential(access_key=access_key, secret_key=secret_key)
    paradigm_client = ParadigmClient(credential=paradigm_credential, host=host)

    if venue == Venue.RIBBON:
        sign_fn = sign_ribbon_bid
        wallet_private_key = _get_value_from_env('EVM_WALLET_PRIVATE_KEY')
    else:
        raise NotImplementedError(f'Bid signing not implemented for venue {venue}')

    price = Decimal(price)

    bid_payload = sign_fn(
        paradigm_client=paradigm_client,
        rfq_id=rfq_id,
        price=price,
        wallet_name=wallet_name,
        wallet_private_key=wallet_private_key,
    )

    response = paradigm_client.place_bid(rfq_id, price, wallet_name, bid_payload)
    print(f"Bid response:\n{response}")

    if quote_id := response.get('id'):
        print(f"Removing in {seconds} seconds")
        time.sleep(seconds)
        response = paradigm_client.remove_bid(quote_id)
        print(f"Removing response:\n{response}")


if __name__ == '__main__':
    main()
