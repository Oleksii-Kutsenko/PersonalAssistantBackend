FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN mkdir /pa
WORKDIR /pa

ADD ./pa /pa
RUN pip install -r requirements.txt