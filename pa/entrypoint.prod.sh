#!/bin/sh

python3 manage.py collectstatic --no-input --clear
python3 manage.py migrate
if pytest && pylint --rcfile=.pylintrc fin/* pa/*; then
  exec "$@"
else
  exit "$?"
fi
