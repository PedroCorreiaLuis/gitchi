CREATE TABLE IF NOT EXISTS last_play_results (
    repo_path TEXT PRIMARY KEY,
    returncode INTEGER NOT NULL,
    ran_at INTEGER NOT NULL
);
