# Signing Quotes - Code Samples

## Setup

Install dependencies:

```
pipenv shell --python=3.9
pip install -r requirements.txt
```

Export variables:

```
export PARADIGM_ACCESS_KEY=<access-key>
export PARADIGM_SECRET_KEY=<secret-key>

# export the wallet private key address for the chain you want to sign bids
export EVM_WALLET_PRIVATE_KEY=<wallet-private-key>
```

## Run

Set the venue and bid parameters in the command line interface.

```
python3 sign_quote.py ribbon --rfq_id=14 --price=0.1 --wallet_name=ribbon-w1
```

## Supported venues

- [Ribbon finance](https://www.ribbon.finance/)
