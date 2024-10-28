FROM python:3.9-slim-buster

ENV PYTHONUNBUFFERED=1
ENV LOGGING_LEVEL="INFO"
ENV ENVIRONMENT="NIGHTLY"
ENV TAKER_ACCOUNT_NAME=""
ENV TAKER_ACCESS_KEY=""
ENV TAKER_SECRET_KEY=""

COPY . /

RUN pip install -r /requirements.txt

CMD ["sh", "-c", "python /market-taker.py $LOGGING_LEVEL \
                                          $ENVIRONMENT \
                                          $TAKER_ACCOUNT_NAME \
                                          $TAKER_ACCESS_KEY \
                                          $TAKER_SECRET_KEY"]