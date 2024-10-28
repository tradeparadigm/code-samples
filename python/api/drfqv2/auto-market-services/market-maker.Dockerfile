FROM python:3.9-slim-buster

ENV PYTHONUNBUFFERED=1
ENV LOGGING_LEVEL="INFO"
ENV ENVIRONMENT="NIGHTLY"
ENV MAKER_ACCOUNT_NAME=""
ENV MAKER_ACCESS_KEY=""
ENV MAKER_SECRET_KEY=""
ENV ORDER_PRICE_WORSE_THAN_MARK_FLAG="True"
ENV ORDER_PRICING_TICK_MULTIPLE="10"
ENV ORDER_REFRESH_WINDOW_LOWER_BOUNDARY="0"
ENV ORDER_REFRESH_WINDOW_UPPER_BOUNDARY="1"

COPY . /

RUN pip install -r /requirements.txt

CMD ["sh", "-c", "python /market-maker.py $LOGGING_LEVEL \
                                          $ENVIRONMENT \
                                          $MAKER_ACCOUNT_NAME \
                                          $MAKER_ACCESS_KEY \
                                          $MAKER_SECRET_KEY \
                                          $ORDER_PRICE_WORSE_THAN_MARK_FLAG \
                                          $ORDER_PRICING_TICK_MULTIPLE \
                                          $ORDER_REFRESH_WINDOW_LOWER_BOUNDARY \
                                          $ORDER_REFRESH_WINDOW_UPPER_BOUNDARY"]