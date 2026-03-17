-- Migration: Create sessions table for Genify state persistence
-- Version: 001
-- Created: 2026-01-23
-- Description: Initial schema for storing user session state in Lakebase

-- Create schema for Genify state storage
CREATE SCHEMA IF NOT EXISTS genify;

-- Main sessions table for storing key-value state
-- Each row represents one state key within a user's session
CREATE TABLE IF NOT EXISTS genify.user_sessions (
    id SERIAL PRIMARY KEY,
    
    -- Session identification
    session_key VARCHAR(64) NOT NULL,          -- Format: {email_hash_12}_{timestamp}
    user_email VARCHAR(255) NOT NULL,          -- User's email from X-Forwarded-Email
    
    -- State data
    state_key VARCHAR(512) NOT NULL,           -- Format: {session_key}:{key_name}
    value JSONB NOT NULL,                      -- JSON serialized state value
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique state keys per session
    UNIQUE(session_key, state_key)
);

-- Index for querying user's sessions (for history panel)
CREATE INDEX IF NOT EXISTS idx_user_sessions_email 
ON genify.user_sessions(user_email);

-- Index for loading a specific session
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_key 
ON genify.user_sessions(session_key);

-- Index for prefix queries (clear_prefix operations)
CREATE INDEX IF NOT EXISTS idx_user_sessions_state_key 
ON genify.user_sessions(state_key varchar_pattern_ops);

-- Index for finding recent sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_updated_at 
ON genify.user_sessions(updated_at DESC);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION genify.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at on row changes
DROP TRIGGER IF EXISTS update_user_sessions_updated_at ON genify.user_sessions;
CREATE TRIGGER update_user_sessions_updated_at
    BEFORE UPDATE ON genify.user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION genify.update_updated_at_column();

-- Add comment for documentation
COMMENT ON TABLE genify.user_sessions IS 
'Stores user session state for Genify app. Each row is a key-value pair within a session.';

COMMENT ON COLUMN genify.user_sessions.session_key IS 
'Unique session identifier: {email_hash_12}_{timestamp_YYYYMMDD_HHMMSS}';

COMMENT ON COLUMN genify.user_sessions.state_key IS 
'Full state key including session namespace: {session_key}:{key_name}';

COMMENT ON COLUMN genify.user_sessions.value IS 
'JSON serialized state value. Can contain complex objects like interview state.';

-- Grant permissions (adjust role names as needed for your environment)
-- GRANT USAGE ON SCHEMA genify TO genify_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON genify.user_sessions TO genify_app;
-- GRANT USAGE ON SEQUENCE genify.user_sessions_id_seq TO genify_app;
