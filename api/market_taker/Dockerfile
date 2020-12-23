FROM python:3.8-slim-buster

ENV PARADIGM_ACCESS_KEY=""
ENV PARADIGM_SECRET_KEY=""
ENV PARADIGM_ACCOUNT_NAME_DBT="ParadigmTestOne"
ENV PARADIGM_ACCOUNT_NAME_BIT="ParadigmTestOne"
ENV PARADIGM_ACCOUNT_NAME_CME="ParadigmTestOne"
ENV PARADIGM_DESK_NAME="DSK1"
ENV DBT_HTTP_HOST="https://test.deribit.com/api/v2"
ENV BIT_HTTP_HOST="https://testapi.bitexch.dev/v1"
ENV PARADIGM_WS_URL="wss://ws.api.nightly.paradigm.co/"
ENV PARADIGM_HTTP_HOST="https://api.nightly.paradigm.co"

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY market_taker.py /

CMD ["sh", "-c", "python /market_taker.py"]
