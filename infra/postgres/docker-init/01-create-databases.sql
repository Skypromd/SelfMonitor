-- Runs once on empty Postgres data dir (docker-entrypoint-initdb.d).
-- POSTGRES_DB (default db_user_profile) is already created by the image.

CREATE DATABASE db_invoices;
CREATE DATABASE db_transactions;
CREATE DATABASE db_compliance;
CREATE DATABASE db_consent;
CREATE DATABASE db_documents;
CREATE DATABASE db_partner;
CREATE DATABASE db_referral;
CREATE DATABASE mlflow;
