from decimal import Decimal
from pprint import pprint

from ribbon.definitions import Bid
from ribbon.wallet import Wallet
from ribbon.definitions import Domain

from paradigm_api import ParadigmClient


def sign_ribbon_bid(
    paradigm_client: ParadigmClient,
    rfq_id: str,
    price: Decimal,
    wallet_name: str,
    wallet_private_key: str,
    use_delegated_wallet=False,
) -> str:
    rfq_data = paradigm_client.get_rfq_data(rfq_id)
    domain = Domain(
        name=rfq_data['domain']['contract_name'],
        chainId=rfq_data['domain']['chain_id'],
        verifyingContract=rfq_data['domain']['verifying_contract'],
        version=rfq_data['domain']['version'],
    )

    bidding_data = paradigm_client.get_bidding_data(
        rfq_id, price, wallet_name, use_nonce=True, use_delegated_wallet=use_delegated_wallet
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
