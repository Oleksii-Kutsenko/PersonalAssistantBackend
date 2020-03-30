#!/bin/sh

if [ "${DATABASE}" = "postgres" ]; then
  echo "Waiting for postgres..."

  while ! nc -z $SQL_HOST $SQL_PORT; do
    sleep 0.1
  done

  echo "PostgreSQL started"
fi

python3 manage.py collectstatic --no-input --clear
python3 manage.py migrate
if pytest && pylint --rcfile=.pylintrc fin/* pa/*; then
  exec "$@"
else
  exit "$?"
fi
