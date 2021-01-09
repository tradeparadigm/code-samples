# syntax=docker/dockerfile:1.2
FROM python:3.8-slim-buster

ENV PARADIGM_ACCESS_KEY=""
ENV PARADIGM_SECRET_KEY=""
ENV PARADIGM_ACCOUNT_NAME_BIT=""
ENV PARADIGM_ACCOUNT_NAME_CME=""
ENV PARADIGM_ACCOUNT_NAME_DBT=""

# Install requirements
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy Source
COPY market_maker.py /

CMD ["python", "/market_maker.py"]
