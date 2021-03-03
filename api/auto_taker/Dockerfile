# syntax=docker/dockerfile:1.2
FROM python:3.9.1

ENV PARADIGM_ACCESS_KEY="2IHUpZXP8LqVYsokGRKAV4JS"
ENV PARADIGM_SECRET_KEY="CxIm0jGeJXrxnWIcDm8oDSNz+GrOJVxeKISuMdPkMumtHxVf"
ENV PARADIGM_ACCOUNT_NAME_DBT="ParadigmTestNinetyFive"
ENV MAKER_DESK_TICKER="DSK2"

# Install requirements
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy Source
COPY auto_taker.py /

CMD ["python", "/auto_taker.py"]
