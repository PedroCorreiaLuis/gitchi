CREATE TABLE IF NOT EXISTS news_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_path TEXT NOT NULL,
    event_type TEXT NOT NULL,        -- 'evolved', 'hatched', 'became_hungry',
                                     -- 'became_ghost', 'revived', 'sick', 'recovered'
    from_value TEXT,                 -- prior state, for transitions (e.g. 'baby')
    to_value TEXT,                   -- new state (e.g. 'teen')
    detail TEXT,                     -- human-readable summary
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS news_events_recent
    ON news_events (created_at DESC);
CREATE INDEX IF NOT EXISTS news_events_repo
    ON news_events (repo_path, created_at DESC);

CREATE TABLE IF NOT EXISTS ignore_state (
    repo_path TEXT PRIMARY KEY,
    ignored_at INTEGER NOT NULL,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS vitals_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_path TEXT NOT NULL,
    hunger INTEGER NOT NULL,
    health INTEGER NOT NULL,
    energy INTEGER NOT NULL,
    mood INTEGER NOT NULL,
    age_days INTEGER NOT NULL,
    stage TEXT NOT NULL,
    species TEXT NOT NULL,
    recorded_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS vitals_history_repo_recorded
    ON vitals_history (repo_path, recorded_at DESC);
