"""SQLite store and a demo clock for the intake pipeline (local prototype only)."""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"          # uploaded originals and normalized files (git-ignored)
OUTBOX = ROOT / "outbox"      # dry-run notifications (git-ignored)
INBOX = ROOT / "fax-inbox"    # stand-in for a fax-to-email mailbox (git-ignored)
DB_PATH = ROOT / "work" / "pipeline.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS referrals (
  id TEXT PRIMARY KEY, hospital TEXT NOT NULL, channel TEXT NOT NULL,
  received_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
  decided_at TEXT, decision TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, referral_id TEXT NOT NULL REFERENCES referrals(id),
  filename TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL, pages INTEGER,
  original_path TEXT NOT NULL, normalized_path TEXT, status TEXT NOT NULL, note TEXT, added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (
  id TEXT PRIMARY KEY, referral_id TEXT NOT NULL REFERENCES referrals(id),
  type TEXT NOT NULL CHECK (type IN ('red', 'missing')), text TEXT NOT NULL, rule_id TEXT,
  created_at TEXT NOT NULL, resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS pages (
  referral_id TEXT NOT NULL, n INTEGER NOT NULL, document_id TEXT, image_path TEXT NOT NULL,
  doc_type TEXT, rotation INTEGER DEFAULT 0, legible INTEGER, prior_stay INTEGER, added_by TEXT DEFAULT 'arrival',
  PRIMARY KEY (referral_id, n)
);
CREATE TABLE IF NOT EXISTS facts (
  id TEXT PRIMARY KEY, referral_id TEXT NOT NULL, key TEXT NOT NULL, source TEXT NOT NULL,
  status TEXT NOT NULL, value TEXT, page INTEGER, quote TEXT, quote_checked INTEGER DEFAULT 0,
  verified_at TEXT, verified_by TEXT, updated_at TEXT NOT NULL,
  UNIQUE (referral_id, key, source)
);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY, referral_id TEXT NOT NULL, kind TEXT NOT NULL, rule_id TEXT, fact_key TEXT,
  text TEXT NOT NULL, page INTEGER, quote TEXT, page2 INTEGER, quote2 TEXT, quote_checked INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preread_runs (
  referral_id TEXT PRIMARY KEY, status TEXT NOT NULL, step TEXT, reader TEXT, started_at TEXT, finished_at TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS activity (
  id TEXT PRIMARY KEY, referral_id TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL, role TEXT,
  kind TEXT NOT NULL CHECK (kind IN ('work', 'view', 'system')), action TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
  id TEXT PRIMARY KEY, referral_id TEXT NOT NULL REFERENCES referrals(id),
  tier TEXT NOT NULL, audience TEXT NOT NULL, channel TEXT NOT NULL,
  subject TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL,
  status TEXT NOT NULL, outbox_path TEXT, dedupe_key TEXT UNIQUE
);
"""

_lock = threading.RLock()


MIGRATIONS = [
    # flags gain an owner, where they came from, whether staff approved sending them, and how they were resolved
    ("flags", "owner", "ALTER TABLE flags ADD COLUMN owner TEXT DEFAULT 'coordinator'"),
    ("flags", "source", "ALTER TABLE flags ADD COLUMN source TEXT DEFAULT 'staff'"),
    ("flags", "approved", "ALTER TABLE flags ADD COLUMN approved INTEGER DEFAULT 1"),
    ("flags", "fact_key", "ALTER TABLE flags ADD COLUMN fact_key TEXT"),
    ("flags", "resolved_note", "ALTER TABLE flags ADD COLUMN resolved_note TEXT"),
    ("documents", "via", "ALTER TABLE documents ADD COLUMN via TEXT DEFAULT 'arrival'"),
]


def connect(path=None):
    p = Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p), check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")      # lets the background pre-read write while pages are being served
    con.execute("PRAGMA busy_timeout=30000")
    con.executescript(SCHEMA)
    for table, col, sql in MIGRATIONS:
        cols = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            con.execute(sql)
    con.commit()
    return con


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---- demo clock: real time plus an offset that the demo can fast-forward ----

def now(con):
    row = con.execute("SELECT value FROM settings WHERE key='clock_offset_min'").fetchone()
    offset = float(row["value"]) if row else 0.0
    return datetime.now(timezone.utc) + timedelta(minutes=offset)


def advance_clock(con, minutes):
    with _lock:
        row = con.execute("SELECT value FROM settings WHERE key='clock_offset_min'").fetchone()
        cur = float(row["value"]) if row else 0.0
        con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('clock_offset_min', ?)", (str(cur + minutes),))
        con.commit()


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse(ts):
    return datetime.fromisoformat(ts)


def minutes_open(con, referral):
    end = parse(referral["decided_at"]) if referral["decided_at"] else now(con)
    return (end - parse(referral["received_at"])).total_seconds() / 60.0


# ---- who touched what ----

def log_activity(con, rid, actor, action, kind="work", role=None):
    """Record a staff action ('work'), a staff opening the referral ('view', at most once per 10 minutes per person) or a system event."""
    actor = (actor or "").strip() or "Unknown staff"
    if kind == "view":
        last = con.execute("SELECT at FROM activity WHERE referral_id=? AND actor=? AND kind='view' ORDER BY at DESC LIMIT 1", (rid, actor)).fetchone()
        if last and (now(con) - parse(last["at"])).total_seconds() < 600:
            return None
    aid = new_id("act")
    con.execute("INSERT INTO activity (id, referral_id, at, actor, role, kind, action) VALUES (?,?,?,?,?,?,?)",
                (aid, rid, iso(now(con)), actor[:40], role, kind, action[:200]))
    con.commit()
    return aid


def activity_status(con, rid):
    """Untouched (no staff has opened or worked on it), Opened (viewed only) or Worked on, plus who and when."""
    rows = con.execute("SELECT * FROM activity WHERE referral_id=? AND kind IN ('work','view') ORDER BY at", (rid,)).fetchall()
    work = [r for r in rows if r["kind"] == "work"]
    workers = list(dict.fromkeys(r["actor"] for r in work))
    openers = list(dict.fromkeys(r["actor"] for r in rows))
    if work:
        last = work[-1]
        state = "worked"
    elif rows:
        last = rows[-1]
        state = "opened"
    else:
        return {"state": "untouched", "last": None, "workers": [], "openers": []}
    mins = int((now(con) - parse(last["at"])).total_seconds() // 60)
    return {"state": state, "last": {"actor": last["actor"], "action": last["action"], "minutes_ago": mins, "at": last["at"]},
            "workers": workers, "openers": openers}


def to_json(rows):
    return json.dumps([dict(r) for r in rows], indent=1)
