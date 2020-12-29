# Paradigm API Code Samples

## Setup

You must have the following prerequisites installed to run these scripts:
  * [Docker](https://docs.docker.com/get-docker/)
  * [Python 3](https://docs.python-guide.org/starting/installation/)
  * [Pipenv](https://pipenv.pypa.io/en/latest/install/)

Run the following commands to setup your environment to run the scripts:

```bash
pipenv install --ignore-pipfile
```

## Available scripts

### create_rfq.py

The `create_rfq.py` script is CLI tool tha can be used to create multi-leg RFQs
using the Paradigm API.

See the script's help documentation for available arguments.

#### Usage

To run the script, type the following into your terminal:

```bash
pipenv run ./create_rfq.py --help
```

### ws_connect.py

The `ws_connect.py` script is CLI tool tha can be used to connect to the
Paradigm API Websocket interface. It will print all messages received and sends
heartbeats on your behalf.

See the script's help documentation for available arguments.

#### Usage

To run the script, type the following into your terminal:

```bash
pipenv run ./ws_connect.py --help
```

### auto_create_rfqs

The `auto_create_rfqs` tool is designed to send an RFQ to a specific maker
every 5 seconds. The RFQs are preconfigured and are chosen at random on each
interval.

See the `auto_create_rfqs.py` script in the `auto_create_rfqs` directory for
further information.

#### Usage

The `auto_create_rfqs` tool is packaged and deployed as a Docker container.

The container can be configured by passing environment variables at runtime.
For all available configuration variables, see the `auto_create_rfqs.py` source
code.

To build the container iamge, type the following command into your terminal:

```bash
docker build -t auto_create_rfqs auto_create_rfqs
```

To subsequently run the built image, type the following command into your
terminal:

```bash
docker run -it --rm \
  -e PARADIGM_ACCESS_KEY=<API-Access-Key> \
  -e PARADIGM_SECRET_KEY=<API-Secret-Key> \
  auto_create_rfqs
```
_Note_: Replace `<API-Access-Key>` and `<API-Secret-Key>` with your keys.

### market_maker

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
docker run -it --rm \
  -e PARADIGM_ACCESS_KEY=<API-Access-Key> \
  -e PARADIGM_SECRET_KEY=<API-Secret-Key> \
  market_maker
```
_Note_: Replace `<API-Access-Key>` and `<API-Secret-Key>` with your keys.

### market_taker

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
docker run -it --rm \
  -e PARADIGM_ACCESS_KEY=<API-Access-Key> \
  -e PARADIGM_SECRET_KEY=<API-Secret-Key> \
  market_taker
```
_Note_: Replace `<API-Access-Key>` and `<API-Secret-Key>` with your keys.
