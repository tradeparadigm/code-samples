FROM python:3.9-slim-buster

ENV PYTHONUNBUFFERED=1
ENV LOGGING_LEVEL="INFO"
ENV ENVIRONMENT="NIGHTLY"
ENV TAKER_ACCOUNT_NAME="ParadigmTestNinetyFive"
ENV TAKER_ACCESS_KEY="Z9gBdD05yiHLotRCxrSeFTfC"
ENV TAKER_SECRET_KEY="9qgG7DU0XNaqF9n5Q35iQtL5Bv7JFNUffagT7/qC9jlH0exj"

COPY . /

RUN pip install -r /requirements.txt

CMD ["sh", "-c", "python /market-taker.py $LOGGING_LEVEL \
                                          $ENVIRONMENT \
                                          $TAKER_ACCOUNT_NAME \
                                          $TAKER_ACCESS_KEY \
                                          $TAKER_SECRET_KEY"]