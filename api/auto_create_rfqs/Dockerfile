FROM python:3.8-slim-buster

ENV PARADIGM_ACCESS_KEY=""
ENV PARADIGM_SECRET_KEY=""
ENV PARADIGM_ACCOUNT_NAME_DBT="ParadigmTestTwo"
ENV PARADIGM_ACCOUNT_NAME_BIT="ParadigmTestTwo"
ENV PARADIGM_ACCOUNT_NAME_CME="ParadigmTestTwo"
ENV PARADIGM_DESK_NAME="DSK2"
ENV MAKER_DESK_NAME="DSK1"
ENV DBT_HTTP_HOST="https://test.deribit.com/api/v2"
ENV BIT_HTTP_HOST="https://testapi.bitexch.dev/v1"
ENV PARADIGM_WS_URL="wss://ws.api.test.paradigm.co/"
ENV PARADIGM_HTTP_HOST="https://api.test.paradigm.co"

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY AutoTakerCreateRFQs.py /

CMD ["sh", "-c", "python /AutoTakerCreateRFQs.py"]
