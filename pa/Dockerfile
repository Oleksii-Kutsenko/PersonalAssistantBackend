FROM ubuntu:20.04

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update

# psycopg2
RUN apt-get install -yqq libpq-dev gcc python3-dev musl-dev

# cryptography
RUN apt-get install -yqq libffi-dev libssl-dev

# python
RUN apt-get install -yqq python3 python3-pip

# delete cache
RUN apt-get autoremove -yqq && apt-get clean -yqq

COPY . /usr/src/app

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
