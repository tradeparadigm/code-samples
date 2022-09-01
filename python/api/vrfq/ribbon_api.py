from decimal import Decimal
from pprint import pprint

from ribbon.config import RibbonSDKConfig

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

    bidding_data = paradigm_client.get_bidding_data(
        rfq_id,
        price,
        wallet_name,
        use_nonce=True,
        use_delegated_wallet=use_delegated_wallet
    )

    sdk = RibbonSDKConfig()

    print('Bid details to be signed:')
    pprint(bidding_data)

    return sdk.sign_bid(
        contract_address=rfq_data['domain']['verifying_contract'],
        chain_id=rfq_data['domain']['chain_id'],
        public_key=None,
        private_key=wallet_private_key,
        swap_id=bidding_data['swap_id'],
        nonce=bidding_data['nonce'],
        signer_wallet=bidding_data['signer_wallet'],
        sell_amount=bidding_data['sell_amount'],
        buy_amount=bidding_data['buy_amount'],
        referrer=bidding_data['referrer'],
    )
