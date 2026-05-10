CREATE TABLE IF NOT EXISTS repos (
    path TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    primary_language TEXT,
    first_commit INTEGER,           -- unix epoch seconds
    last_commit INTEGER,
    commit_count INTEGER NOT NULL DEFAULT 0,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    has_tests INTEGER NOT NULL DEFAULT 0,
    has_ci INTEGER NOT NULL DEFAULT 0,
    last_scanned INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS vitals_cache (
    repo_path TEXT PRIMARY KEY REFERENCES repos(path) ON DELETE CASCADE,
    hunger INTEGER NOT NULL,
    health INTEGER NOT NULL,
    energy INTEGER NOT NULL,
    mood INTEGER NOT NULL,
    age_days INTEGER NOT NULL,
    stage TEXT NOT NULL,
    species TEXT NOT NULL,
    computed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS mood_cache (
    repo_path TEXT PRIMARY KEY REFERENCES repos(path) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    sample_hash TEXT NOT NULL,
    computed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bury_state (
    repo_path TEXT PRIMARY KEY REFERENCES repos(path) ON DELETE CASCADE,
    buried_at INTEGER NOT NULL,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
