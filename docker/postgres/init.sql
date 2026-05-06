-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create MLflow schema  
CREATE SCHEMA IF NOT EXISTS mlflow;

GRANT ALL PRIVILEGES ON SCHEMA public TO upi_user;
GRANT ALL PRIVILEGES ON SCHEMA mlflow TO upi_user;

-- Performance settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
