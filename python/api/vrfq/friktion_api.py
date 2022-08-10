from decimal import Decimal
from pprint import pprint


from anchorpy import Wallet
from friktion.bid_details import BidDetails
from solana.publickey import PublicKey
from solana.keypair import Keypair
import solders.keypair

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
    bid = BidDetails(
        bid_size=int(bidding_data['buy_amount']),
        referrer=PublicKey(bidding_data['referrer']),
        bid_price=int(bidding_data['sell_amount']) // int(bidding_data['buy_amount']),
        signer_wallet=PublicKey(bidding_data['signer_wallet']),
        order_id=int(bidding_data['swap_id']),
    )
    print('Bid details to be signed:')
    pprint(vars(bid))

    wallet = Wallet(Keypair(solders.keypair.Keypair.from_base58_string(wallet_private_key)))
    msg, signature = bid.as_signed_msg(wallet)
    print(f'Msg signed: {msg}')

    return str(signature)
