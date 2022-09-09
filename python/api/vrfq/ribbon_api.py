from ribbon.config import RibbonSDKConfig


def sign_ribbon_bid(
    rfq_data: dict,
    bidding_data: dict,
    wallet_private_key: str,
) -> str:

    sdk = RibbonSDKConfig()

    signature = sdk.sign_bid(
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
    print(f'Signature: {signature}')

    return signature
