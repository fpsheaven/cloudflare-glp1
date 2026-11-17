CREATE TABLE accounts(id BIGINT PRIMARY KEY, display_name TEXT);
-- Lookup performed once per completed action using the primary-key index.
SELECT display_name FROM accounts WHERE id = $1;
