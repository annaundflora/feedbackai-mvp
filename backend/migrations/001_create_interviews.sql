-- backend/migrations/001_create_interviews.sql
-- Migration: Create interviews table
-- Date: 2026-02-13
-- Description: Speichert Interview-Sessions mit Transkript und Summary

CREATE TABLE IF NOT EXISTS mvp_interviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_id TEXT NOT NULL,
  session_id UUID NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'completed', 'completed_timeout')),
  transcript JSONB,
  summary TEXT,
  message_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_mvp_interviews_anonymous_id ON mvp_interviews(anonymous_id);
CREATE INDEX IF NOT EXISTS idx_mvp_interviews_session_id ON mvp_interviews(session_id);
CREATE INDEX IF NOT EXISTS idx_mvp_interviews_status ON mvp_interviews(status);
