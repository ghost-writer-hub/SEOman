-- Initialize database for SEOman and Casdoor

-- Create seoman database if not exists
CREATE DATABASE IF NOT EXISTS seoman;

-- Create casdoor database if not exists
CREATE DATABASE IF NOT EXISTS casdoor;

-- Connect to casdoor database
\c casdoor

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create casdoor user with all privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'casdoor') THEN
        CREATE USER casdoor WITH PASSWORD 'casdoor_default_password';
    END IF;
    GRANT ALL PRIVILEGES ON DATABASE casdoor TO casdoor;
    GRANT ALL ON SCHEMA public TO casdoor;
END
$$;

-- Connect back to postgres
\c postgres

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE seoman TO seoman;
GRANT ALL PRIVILEGES ON DATABASE casdoor TO seoman;
GRANT ALL ON SCHEMA public TO seoman;
