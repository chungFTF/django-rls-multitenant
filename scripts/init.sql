-- =====================================
-- Simple RLS Demo Setup
-- =====================================

-- Create single application role
DROP ROLE IF EXISTS app_role;
CREATE ROLE app_role;
GRANT CONNECT ON DATABASE rls_db TO app_role;
GRANT USAGE ON SCHEMA public TO app_role;
GRANT CREATE ON SCHEMA public TO app_role;

-- Create single application user
DROP USER IF EXISTS app_user;
CREATE USER app_user WITH PASSWORD 'app_pass';
GRANT app_role TO app_user;

-- Connect to the application database
\c rls_db;

-- Set default permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT USAGE, SELECT ON SEQUENCES TO app_role;

-- =====================================
-- RLS Helper Function
-- =====================================

-- Get current branch ID from session variable
CREATE OR REPLACE FUNCTION get_current_branch_id() 
RETURNS UUID AS $$
BEGIN
    RETURN COALESCE(current_setting('app.current_branch_id', true)::UUID, NULL);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================
-- Context Check View
-- =====================================

-- Create view to check current context settings
CREATE OR REPLACE VIEW current_branch_context AS
SELECT 
    current_user as current_user,
    get_current_branch_id() as current_branch_id,
    current_setting('app.current_branch_id', true) as branch_setting,
    'Branch User' as user_type_description;

-- Grant permissions to app_role
GRANT SELECT ON current_branch_context TO app_role;

SELECT 'Simple RLS Branch Isolation System Initialized' as status;