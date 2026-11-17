CREATE TABLE events(id TEXT PRIMARY KEY, owner TEXT NOT NULL, created TEXT NOT NULL, payload TEXT);
CREATE INDEX events_created ON events(created);
