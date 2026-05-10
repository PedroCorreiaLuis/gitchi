-- v0.5.0: deterministic gacha-style pet rarities.
-- Stored on vitals_cache (recomputed every refresh — deterministic) and on
-- vitals_history so the per-snapshot rarity travels with the time series.
-- Default 'common' covers pre-existing rows from earlier versions on the
-- next refresh the orchestrator overwrites with the real value.

ALTER TABLE vitals_cache    ADD COLUMN rarity TEXT NOT NULL DEFAULT 'common';
ALTER TABLE vitals_history  ADD COLUMN rarity TEXT NOT NULL DEFAULT 'common';
