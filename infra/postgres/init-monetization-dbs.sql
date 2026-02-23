# Database initialization script for new monetization services
CREATE DATABASE db_referrals;
CREATE DATABASE db_customer_success;
CREATE DATABASE db_pricing;
CREATE DATABASE db_predictive;
CREATE DATABASE db_cost_optimization;

# Grant access to the PostgreSQL user
GRANT ALL PRIVILEGES ON DATABASE db_referrals TO postgres;
GRANT ALL PRIVILEGES ON DATABASE db_customer_success TO postgres;
GRANT ALL PRIVILEGES ON DATABASE db_pricing TO postgres;
GRANT ALL PRIVILEGES ON DATABASE db_predictive TO postgres;
GRANT ALL PRIVILEGES ON DATABASE db_cost_optimization TO postgres;