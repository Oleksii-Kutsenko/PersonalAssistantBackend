FROM python:3.8.1-alpine3.11

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# psycopg2
RUN apk update
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev

COPY . /usr/src/app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
