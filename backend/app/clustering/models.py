"""DB Migration Script fuer LLM Interview Clustering Feature.

Erstellt alle 6 Tabellen:
  1. users
  2. projects
  3. project_interviews
  4. clusters
  5. facts
  6. cluster_suggestions

Wird beim App-Start ausgefuehrt (idempotent via IF NOT EXISTS).
"""

CREATE_TABLES_SQL = """
-- Neue Tabellen fuer LLM Interview Clustering Feature
-- Migration: create_clustering_tables

-- 1. users Tabelle (fuer spaetere Auth in Slice 8)
CREATE TABLE IF NOT EXISTS users (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT        NOT NULL UNIQUE,
    password_hash TEXT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. projects Tabelle
CREATE TABLE IF NOT EXISTS projects (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name                TEXT        NOT NULL,
    research_goal       TEXT        NOT NULL,
    prompt_context      TEXT,
    extraction_source   TEXT        NOT NULL DEFAULT 'summary'
                        CHECK (extraction_source IN ('summary', 'transcript')),
    model_interviewer   TEXT        NOT NULL DEFAULT 'anthropic/claude-sonnet-4',
    model_extraction    TEXT        NOT NULL DEFAULT 'anthropic/claude-haiku-4',
    model_clustering    TEXT        NOT NULL DEFAULT 'anthropic/claude-sonnet-4',
    model_summary       TEXT        NOT NULL DEFAULT 'anthropic/claude-haiku-4',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);

-- 3. project_interviews Tabelle
CREATE TABLE IF NOT EXISTS project_interviews (
    project_id          UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    interview_id        UUID        NOT NULL UNIQUE,
    extraction_status   TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (extraction_status IN ('pending', 'running', 'completed', 'failed')),
    clustering_status   TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (clustering_status IN ('pending', 'running', 'completed', 'failed')),
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, interview_id)
);
CREATE INDEX IF NOT EXISTS idx_project_interviews_project_id ON project_interviews(project_id);

-- 4. clusters Tabelle
CREATE TABLE IF NOT EXISTS clusters (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT        NOT NULL,
    summary         TEXT,
    fact_count      INTEGER     NOT NULL DEFAULT 0,
    interview_count INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_clusters_project_id ON clusters(project_id);

-- 5. facts Tabelle
CREATE TABLE IF NOT EXISTS facts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    interview_id UUID       NOT NULL,
    cluster_id  UUID        REFERENCES clusters(id) ON DELETE SET NULL,
    content     TEXT        NOT NULL,
    quote       TEXT,
    confidence  FLOAT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_facts_project_id ON facts(project_id);
CREATE INDEX IF NOT EXISTS idx_facts_cluster_id ON facts(cluster_id);
CREATE INDEX IF NOT EXISTS idx_facts_interview_id ON facts(interview_id);

-- 6. cluster_suggestions Tabelle
CREATE TABLE IF NOT EXISTS cluster_suggestions (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type                TEXT    NOT NULL CHECK (type IN ('merge', 'split')),
    source_cluster_id   UUID    NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    target_cluster_id   UUID    REFERENCES clusters(id) ON DELETE CASCADE,
    similarity_score    FLOAT,
    proposed_data       JSONB,
    status              TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'accepted', 'dismissed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cluster_suggestions_project_id ON cluster_suggestions(project_id);
"""


async def run_migration(session_factory) -> None:
    """Fuehrt die Migration aus (idempotent via IF NOT EXISTS).

    Args:
        session_factory: SQLAlchemy async_sessionmaker Instanz
    """
    from sqlalchemy import text

    async with session_factory() as session:
        # asyncpg requires executing statements one at a time
        for statement in CREATE_TABLES_SQL.split(";"):
            cleaned = statement.strip()
            if cleaned and not cleaned.startswith("--"):
                await session.execute(text(cleaned))
        await session.commit()
