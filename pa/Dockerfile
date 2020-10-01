FROM ubuntu:20.04

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update

# psycopg2
RUN apt-get install -yqq --no-install-recommends libpq-dev gcc python3-dev musl-dev

# cryptography
RUN apt-get install -yqq --no-install-recommends libffi-dev libssl-dev

# python
RUN apt-get install -yqq --no-install-recommends python3 python3-pip

# delete cache
RUN apt-get autoremove -yqq && apt-get clean -yqq && rm -rf /var/lib/apt/lists/*

COPY . /usr/src/app

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN pip3 install -r dev-requirements.txt

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
