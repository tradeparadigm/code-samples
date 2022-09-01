from decimal import Decimal
from pprint import pprint

from friktion.config import FriktionSDKConfig

from paradigm_api import ParadigmClient


def sign_friktion_bid(
    paradigm_client: ParadigmClient,
    rfq_id: str,
    price: Decimal,
    wallet_name: str,
    wallet_private_key: str,
) -> str:
    bidding_data = paradigm_client.get_bidding_data(
        rfq_id, price, wallet_name, use_nonce=False, use_delegated_wallet=False
    )

    sdk = FriktionSDKConfig()
    signature = sdk.sign_bid(
        private_key=wallet_private_key,
        swap_id=int(bidding_data['swap_id']),
        signer_wallet=bidding_data['signer_wallet'],
        sell_amount=int(bidding_data['sell_amount']),
        buy_amount=int(bidding_data['buy_amount']),
        referrer=bidding_data['referrer'],
    )

    print('Bid details to be signed:')
    pprint(bidding_data)

    return signature
