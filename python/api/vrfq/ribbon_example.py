from decimal import Decimal
import os
from pprint import pprint

from ribbon.definitions import Bid
from ribbon.wallet import Wallet
from ribbon.definitions import Domain

from paradigm_api import ParadigmClient, ParadigmCredential


def _get_value_from_env(key: str, default=None):
    value = os.getenv(key, default=default)

    if not value:
        raise ValueError(f'Must provide a value for {key}')

    return value


# TODO: add sign function to RibbonSDK interface
def sign_ribbon_bid(
    paradigm_client: ParadigmClient,
    rfq_id: id,
    nonce: int,
    price: Decimal,
    wallet_name: str,
    wallet_private_key: str,
    use_delegated_wallet=False,
):
    rfq_data = paradigm_client.get_rfq_data(rfq_id)
    domain = Domain(
        name=rfq_data['domain']['contract_name'],
        chainId=rfq_data['domain']['chain_id'],
        verifyingContract=rfq_data['domain']['verifying_contract'],
        version=rfq_data['domain']['version'],
    )

    bidding_data = paradigm_client.get_bidding_data(
        rfq_id, nonce, price, wallet_name, use_delegated_wallet=use_delegated_wallet
    )
    bid = Bid(
        buyAmount=bidding_data['buy_amount'],
        nonce=bidding_data['nonce'],
        referrer=bidding_data['referrer'],
        sellAmount=bidding_data['sell_amount'],
        signerWallet=bidding_data['signer_wallet'],
        swapId=bidding_data['swap_id'],
    )
    print('Bid details to be signed:')
    pprint(vars(bid))

    wallet = Wallet(private_key=wallet_private_key)
    signed_bid = wallet.sign_bid(domain, bid)

    return signed_bid.r[2:] + signed_bid.s[2:] + hex(signed_bid.v)[2:]


if __name__ == "__main__":
    host = _get_value_from_env('PARADIGM_API_HOST', default='https://api.test.paradigm.co')
    access_key = _get_value_from_env('PARADIGM_ACCESS_KEY')
    secret_key = _get_value_from_env('PARADIGM_SECRET_KEY')
    wallet_private_key = _get_value_from_env('WALLET_PRIVATE_KEY')

    paradigm_credential = ParadigmCredential(access_key=access_key, secret_key=secret_key)
    paradigm_client = ParadigmClient(credential=paradigm_credential, host=host)

    # Adjust parameters to the rfq/quote at hand
    rfq_id = 14
    nonce = 123
    price = Decimal('0.1')
    wallet_name = 'ribbon-w1'  # Add your wallet on admin site

    signature = sign_ribbon_bid(
        paradigm_client=paradigm_client,
        rfq_id=rfq_id,
        nonce=nonce,
        price=price,
        wallet_name=wallet_name,
        wallet_private_key=wallet_private_key,
    )
    print(f'Signature: {signature}')
