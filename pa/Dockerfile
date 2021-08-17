FROM python:3.8

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

# selenium
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt install ./google-chrome-stable_current_amd64.deb
RUN apt install -yqq --no-install-recommends libnss3-dev

ADD ./requirements.txt /usr/src/app/requirements.txt
ADD ./dev-requirements.txt /usr/src/app/dev-requirements.txt

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN pip3 install -r dev-requirements.txt

COPY . /usr/src/app

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
