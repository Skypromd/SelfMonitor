#!/bin/bash
set -e

# The 'postgres' user is a superuser, so it can create databases.
# The 'psql' command is available in the official postgres image.
# The -v ON_ERROR_STOP=1 flag ensures that the script will exit immediately if any command fails.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE db_transactions;
    CREATE DATABASE db_compliance;
    CREATE DATABASE db_documents;
    CREATE DATABASE db_consent;
    CREATE DATABASE db_partner;
EOSQL

