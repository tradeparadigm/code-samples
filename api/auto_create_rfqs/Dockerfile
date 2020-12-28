# syntax=docker/dockerfile:1.2
FROM python:3.8-slim-buster

ENV PARADIGM_ACCESS_KEY=""
ENV PARADIGM_SECRET_KEY=""

# Install requirements
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy Source
COPY auto_create_rfqs.py /

CMD ["python", "/auto_create_rfqs.py"]
