#!/bin/sh
# Runs once, on the first start of an empty data volume: one database per name in
# POSTGRES_MULTIPLE_DATABASES (comma separated), owned by a user of the same name
# whose password is POSTGRES_PASSWORD.
set -eu

for name in $(echo "${POSTGRES_MULTIPLE_DATABASES:-}" | tr ',' ' '); do
  echo "init-databases: creating database and owner ${name}"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE USER "${name}" WITH PASSWORD '${POSTGRES_PASSWORD}';
CREATE DATABASE "${name}" OWNER "${name}";
SQL
done
