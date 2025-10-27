-- ensure UTF-8 and sensible defaults for the role
ALTER ROLE myprojectuser SET client_encoding TO 'utf8';
ALTER ROLE myprojectuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE myprojectuser SET timezone TO 'UTC';

-- grant privileges
GRANT ALL PRIVILEGES ON DATABASE myproject TO myprojectuser;
