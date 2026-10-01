"""SQLite state. One file (data/engine.db), never committed."""
import json
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
  key TEXT PRIMARY KEY,           -- linkedin.com/in/<slug>
  name TEXT, first_name TEXT, lang TEXT,
  headline TEXT, company TEXT, position TEXT, location TEXT, email TEXT,
  features TEXT,                  -- JSON: raw signals from the export
  track TEXT, score INTEGER, grade TEXT,
  s_rel INTEGER, s_intent INTEGER, s_fit INTEGER, s_timing INTEGER,
  fit_known INTEGER, seniority TEXT, function TEXT, vertical TEXT,
  next_action TEXT, reasons TEXT,
  stage TEXT DEFAULT 'NEW',       -- NEW, IN_SEQUENCE, REPLIED, CONVERSATION, MEETING, PROPOSAL, WON, LOST, NURTURE, NOT_CONNECTED, DNC
  touch INTEGER DEFAULT 0,        -- last touch number sent in current sequence
  variant TEXT,                   -- opener variant of the current sequence
  seq_track TEXT,                 -- track the current sequence runs on
  next_due TEXT,                  -- ISO date the next touch is due
  last_touch_at TEXT,
  manual_track TEXT,              -- operator override
  updated_at TEXT,
  segment TEXT, stream TEXT, stream2 TEXT, offer TEXT,   -- opportunity segment (engine/segments.py)
  opp_score INTEGER, opp_tier TEXT, value TEXT
);
CREATE TABLE IF NOT EXISTS touches (
  id TEXT PRIMARY KEY,            -- <date>-<n>
  key TEXT, plan_date TEXT, touch INTEGER, track TEXT, lang TEXT, variant TEXT,
  kind TEXT,                      -- message | enrich
  status TEXT,                    -- planned, sent, skipped_not_connected, skipped_reclassify, skipped_other, error, expired
  message TEXT, final_message TEXT, sent_at TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS replies (
  key TEXT, replied_at TEXT, sentiment TEXT, summary TEXT, next_step TEXT,
  touch_id TEXT, referred_name TEXT, referred_url TEXT
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS ix_touch_key ON touches(key);
CREATE INDEX IF NOT EXISTS ix_touch_date ON touches(plan_date);
CREATE INDEX IF NOT EXISTS ix_reply_key ON replies(key);
"""


def connect(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    _migrate(db)
    return db


NEW_COLS = (("segment", "TEXT"), ("stream", "TEXT"), ("stream2", "TEXT"), ("offer", "TEXT"),
            ("opp_score", "INTEGER"), ("opp_tier", "TEXT"), ("value", "TEXT"))


def _migrate(db):
    have = {r[1] for r in db.execute("PRAGMA table_info(contacts)")}
    for name, typ in NEW_COLS:
        if name not in have:
            db.execute(f"ALTER TABLE contacts ADD COLUMN {name} {typ}")
    db.commit()


def meta_get(db, k, default=None):
    r = db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return json.loads(r["v"]) if r else default


def meta_set(db, k, v):
    db.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (k, json.dumps(v)))
