# Signing Quotes - Code Samples

## Setup

Install dependencies:

```
pipenv shell --python=3.9
pip install -r requirements.txt
```

Export variables:

```
PARADIGM_ACCESS_KEY=<access-key>
PARADIGM_SECRET_KEY=<secret-key>
WALLET_PRIVATE_KEY=<wallet-private-key>
```

## Run

Set the venue and bid parameters in the command line interface

```
python3 main.py friktion --rfq_id=19 --price=0.1 --wallet_name=test

python3 main.py ribbon --rfq_id=14 --price=0.1 --wallet_name=ribbon-w1
```
