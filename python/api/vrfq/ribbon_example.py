from decimal import Decimal
import os
from pprint import pprint

from ribbon.definitions import Bid
from ribbon.wallet import Wallet
from ribbon.definitions import Domain

from paradigm_api import ParadigmClient, ParadigmCredential

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
    PARADIGM_API_HOST = os.getenv('PARADIGM_API_HOST', 'https://api.test.paradigm.co')
    PARADIGM_ACCESS_KEY = os.getenv('PARADIGM_ACCESS_KEY')
    PARADIGM_SECRET_KEY = os.getenv('PARADIGM_SECRET_KEY')
    WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY')

    paradigm_credential = ParadigmCredential(
        access_key=PARADIGM_ACCESS_KEY,
        secret_key=PARADIGM_SECRET_KEY,
    )
    paradigm_client = ParadigmClient(
        credential=paradigm_credential,
        host=PARADIGM_API_HOST
    )

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
        wallet_private_key=WALLET_PRIVATE_KEY,
    )
    print(f'Signature: {signature}')
