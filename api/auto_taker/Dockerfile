# syntax=docker/dockerfile:1.2
FROM python:3.9.1

ENV PARADIGM_ACCESS_KEY=""
ENV PARADIGM_SECRET_KEY=""
ENV PARADIGM_ACCOUNT_NAME_DBT=""
ENV MAKER_DESK_TICKER=""

# Install requirements
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy Source
COPY auto_taker.py /

CMD ["python", "/auto_taker.py"]
