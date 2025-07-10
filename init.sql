-- 建立應用程式使用者
CREATE USER app_user WITH PASSWORD 'app_pass';
GRANT CONNECT ON DATABASE rls_db TO app_user;

-- 切換到應用程式資料庫
\c rls_db;

-- 建立角色和權限
CREATE ROLE app_role;
GRANT USAGE ON SCHEMA public TO app_role;
GRANT CREATE ON SCHEMA public TO app_role;
GRANT app_role TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT USAGE, SELECT ON SEQUENCES TO app_role;