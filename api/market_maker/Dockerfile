# syntax=docker/dockerfile:1.2
FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED=1
ENV PARADIGM_ACCESS_KEY=""
ENV PARADIGM_SECRET_KEY=""
ENV PARADIGM_ACCOUNT_NAME_BIT=""
ENV PARADIGM_ACCOUNT_NAME_CME=""
ENV PARADIGM_ACCOUNT_NAME_DBT=""
ENV PARADIGM_DESK_NAME=""
ENV DBT_HTTP_HOST="https://test.deribit.com/api/v2"
ENV BIT_HTTP_HOST="https://testapi.bitexch.dev/v1"
ENV PARADIGM_WS_URL="wss://ws.api.test.paradigm.co/"
ENV PARADIGM_HTTP_HOST="https://api.test.paradigm.co"

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY market_maker.py /

CMD ["sh", "-c", "python /market_maker.py $PARADIGM_ACCESS_KEY \
                                          $PARADIGM_SECRET_KEY \
                                          $PARADIGM_ACCOUNT_NAME_DBT \
                                          $PARADIGM_ACCOUNT_NAME_BIT \
                                          $PARADIGM_ACCOUNT_NAME_CME \
                                          $PARADIGM_DESK_NAME \
                                          $DBT_HTTP_HOST \
                                          $BIT_HTTP_HOST \
                                          $PARADIGM_WS_URL \
                                          $PARADIGM_HTTP_HOST"]