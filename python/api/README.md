# [Paradigm API Code Samples](https://docs.paradigm.co/)

## Setup

You must have the following prerequisites installed to run these scripts:
  * [Docker](https://docs.docker.com/get-docker/)
  * [Python 3](https://docs.python-guide.org/starting/installation/)
  * [Pipenv](https://pipenv.pypa.io/en/latest/install/)

Run the following commands to setup your environment to run the scripts:

```bash
pipenv install --ignore-pipfile
```

## DRFQ scripts

### [create_rfq.py](drfq/create_rfq.py)

The `create_rfq.py` script is CLI tool tha can be used to create multi-leg RFQs
using the Paradigm API.

See the script's help documentation for available arguments.

#### Usage

To run the script, type the following into your terminal:

```bash
pipenv run ./drfq/create_rfq.py --help
```

### [ws_connect.py](drfq/ws_connect.py)

The `ws_connect.py` script is CLI tool tha can be used to connect to the
Paradigm API Websocket interface. It will print all messages received and sends
heartbeats on your behalf.

See the script's help documentation for available arguments.

#### Usage

To run the script, type the following into your terminal:

```bash
pipenv run ./drfq/ws_connect.py --help
```

### [auto_taker](drfq/auto_taker/)

The `auto_taker` tool is designed to send a Deribit RFQ to a specific maker
every 10 seconds. The RFQs are preconfigured and are chosen at random on each
interval.

See the `auto_taker.py` script in the `auto_taker` directory for
further information.

#### Usage

The `auto_taker` tool is packaged and deployed as a Docker container.

The container can be configured by passing environment variables at runtime.
For all available configuration variables, see the `auto_taker.py` source
code.

To build the container image, type the following command into your terminal:

```bash
docker build -t auto_taker auto_taker
```

To subsequently run the built image, type the following command into your
terminal:

```bash
ACCESS_KEY="< Access Key >"
SECRET_KEY="< Secret Key >"
DERIBIT_ACCOUNT_NAME="< Deribit Account Name >"
MAKER_DESK_TICKER="< Maker Desk Ticker >"

docker run -it  --rm \
  -e PARADIGM_ACCESS_KEY="$ACCESS_KEY" \
  -e PARADIGM_SECRET_KEY="$SECRET_KEY" \
  -e PARADIGM_ACCOUNT_NAME_DBT="$DERIBIT_ACCOUNT_NAME" \
  -e MAKER_DESK_TICKER="$MAKER_DESK_TICKER" \
  auto_taker
```
_Note_: Edit the first few lines with your API credentials, the Deribit
account name configured on your desk's admin dashboard, and the maker desk
ticker you want the RFQs sent to.

### [market_maker](drfq/marker_maker/)

The `market_maker` tool is designed to automatically respond to RFQs via the
Paradigm API. The tool responds to RFQs with random prices from the exchange's
instrument's mark price.

See the `market_maker.py` script in the `market_maker` directory for further
information.

#### Usage

The `market_maker` tool is packaged and deployed as a Docker container.

The container can be configured by passing environment variables at runtime.
For all available configuration variables, see the `market_maker.py` source
code.

To build the container iamge, type the following command into your terminal:

```bash
docker build -t market_maker market_maker
```

To subsequently run the built image, type the following command into your
terminal:

```bash
ACCESS_KEY="< Access Key >"
SECRET_KEY="< Secret Key >"
BIT_ACCOUNT_NAME="< Bit.com Account Name >"
CME_ACCOUNT_NAME="< CME Account Name >"
DERIBIT_ACCOUNT_NAME="< Deribit Account Name >"


docker run -it --rm \
  -e PARADIGM_ACCESS_KEY="$ACCESS_KEY" \
  -e PARADIGM_SECRET_KEY="$SECRET_KEY" \
  -e PARADIGM_ACCOUNT_NAME_BIT="$BIT_ACCOUNT_NAME" \
  -e PARADIGM_ACCOUNT_NAME_CME="$CME_ACCOUNT_NAME" \
  -e PARADIGM_ACCOUNT_NAME_DBT="$DERIBIT_ACCOUNT_NAME" \
  market_maker
```
_Note_: Edit the first few lines with your API credentials and the account names
from your desk's admin dashboard for any venues you want enabled.

### [market_taker](drfq/market_taker/)

The `market_taker` tool is designed to automatically accept quotes via the
Paradigm API. The tool will automatically execute the quote with the best price
every 5 seconds.

See the `market_taker.py` script in the `market_taker` directory for further
information.

#### Usage

The `market_taker` tool is packaged and deployed as a Docker container.

The container can be configured by passing environment variables at runtime.
For all available configuration variables, see the `market_taker.py` source
code.

To build the container iamge, type the following command into your terminal:

```bash
docker build -t market_taker market_taker
```

To subsequently run the built image, type the following command into your
terminal:

```bash
ACCESS_KEY="< Access Key >"
SECRET_KEY="< Secret Key >"

docker run -it --rm \
  -e PARADIGM_ACCESS_KEY="$ACCESS_KEY" \
  -e PARADIGM_SECRET_KEY="$SECRET_KEY" \
  market_taker
```
_Note_: Edit the first couple lines with your API credentials.


## GRFQ scripts

### [auto_taker.py](grfq/auto_taker.py)

The `auto_taker.py` script is CLI tool that can be used to run a basic taker flow for grfq.

See the script's help documentation for available arguments.

#### Usage

To run the script, type the following into your terminal:

```bash
pipenv run ./grfq/auto_taker.py
```