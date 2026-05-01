"""
Data Detective Marketplace App — FastAPI Backend
=================================================
Game + Genie space provisioning for Free Edition workspaces.

When a player selects a mystery scenario, the app provisions the
data tables and Genie space into their workspace automatically.

Scoring (max 500):
  - Clues & evidence (max 5 × 30): +150
  - Root cause deduction (keyword-overlap scored): up to +100
  - Business recommendation (keyword-overlap scored): up to +250
"""

import json
import logging
import os
import re as _re
import sqlite3
import threading
import time as _time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from provisioner import provision_scenario
from scenarios.registry import MYSTERIES, MYSTERY_ANSWER_KEYS, SCENARIOS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("data-detective")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = os.environ.get("DB_PATH", "game.db")
MAX_EVIDENCE = 10
SCORED_EVIDENCE = 5

POINTS_ROOT_CAUSE = 100
POINTS_PER_EVIDENCE = 30
POINTS_RECOMMENDATION_MAX = 250

MAX_EVIDENCE_ITEM_BYTES = 1_500_000   # ~1.5MB per item; fits a base64-encoded image
MAX_SUBMISSION_TOTAL_BYTES = 6_000_000  # ~6MB total per submission
MAX_TEXT_FIELD_LEN = 5000             # solution / recommendation
LEADERBOARD_FORM_URL = os.environ.get("LEADERBOARD_FORM_URL", "").strip()
PRE_PROVISION_ALL = os.environ.get("PRE_PROVISION_ALL", "").lower() in ("1", "true", "yes")

# Total provisioning steps as reported by provisioner.provision_scenario
TOTAL_STEPS = 8


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id          TEXT PRIMARY KEY,
                nickname    TEXT NOT NULL,
                mystery     TEXT NOT NULL DEFAULT '',
                genie_url   TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id                   TEXT PRIMARY KEY,
                account_id           TEXT NOT NULL REFERENCES accounts(id),
                solution             TEXT NOT NULL DEFAULT '',
                recommendation       TEXT NOT NULL DEFAULT '',
                submitted_at         TEXT NOT NULL,
                score                REAL,
                root_cause_score     REAL DEFAULT 0,
                evidence_score       REAL DEFAULT 0,
                recommendation_score REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS evidence (
                id            TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL REFERENCES submissions(id),
                field_order   INTEGER NOT NULL,
                type          TEXT NOT NULL CHECK (type IN ('text', 'image', 'csv')),
                content       TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS provisioned_spaces (
                scenario        TEXT PRIMARY KEY,
                catalog_name    TEXT NOT NULL,
                genie_space_id  TEXT NOT NULL,
                genie_url       TEXT NOT NULL,
                provisioned_at  TEXT NOT NULL,
                provisioned_by  TEXT NOT NULL
            );
        """)


init_db()

# ---------------------------------------------------------------------------
# Provisioning state (in-memory, transient)
# ---------------------------------------------------------------------------

_MAX_STATUS_ENTRIES = 1000
_provisioning_status: dict[str, dict] = {}
_provisioning_status_lock = threading.Lock()


def _set_provisioning_status(account_id: str, status: dict):
    with _provisioning_status_lock:
        # Cap dict size; drop oldest insertion (dicts preserve insertion order in 3.7+).
        while len(_provisioning_status) >= _MAX_STATUS_ENTRIES and account_id not in _provisioning_status:
            _provisioning_status.pop(next(iter(_provisioning_status)))
        _provisioning_status[account_id] = status


def _get_provisioning_status(account_id: str) -> Optional[dict]:
    with _provisioning_status_lock:
        return _provisioning_status.get(account_id)


# ---------------------------------------------------------------------------
# Scoring functions (keyword-based)
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "was", "were", "are", "of", "in", "to",
    "and", "or", "that", "this", "it", "for", "on", "with", "as",
    "at", "by", "from", "be", "been", "being", "has", "had", "have",
    "do", "does", "did", "not", "but", "if", "so", "no", "its",
    "they", "their", "them", "we", "our", "he", "she", "his", "her",
})


def _keyword_overlap(submission: str, reference: str) -> float:
    """Return fraction of reference keywords found in submission (0.0–1.0)."""
    ref_words = set(_re.findall(r'[a-z]+', reference.lower())) - _STOPWORDS
    sub_words = set(_re.findall(r'[a-z]+', submission.lower())) - _STOPWORDS
    if not ref_words:
        return 0.0
    return len(ref_words & sub_words) / len(ref_words)


def _score_root_cause(submission_solution: str, correct_root_cause: str) -> int:
    if not correct_root_cause.strip() or not submission_solution.strip():
        return 0
    overlap = _keyword_overlap(submission_solution, correct_root_cause)
    return min(int(overlap * POINTS_ROOT_CAUSE), POINTS_ROOT_CAUSE)


def _score_evidence(evidence_rows: list) -> int:
    non_empty = [e for e in evidence_rows if e["content"].strip()][:SCORED_EVIDENCE]
    return len(non_empty) * POINTS_PER_EVIDENCE


def _score_recommendation(recommendation: str, root_cause: str, scoring_context: str) -> int:
    if not recommendation.strip():
        return 0
    # Score against both root cause and scoring context for broader keyword coverage
    combined_reference = f"{root_cause} {scoring_context}"
    overlap = _keyword_overlap(recommendation, combined_reference)
    return min(int(overlap * POINTS_RECOMMENDATION_MAX), POINTS_RECOMMENDATION_MAX)


# ---------------------------------------------------------------------------
# Profanity filter
# ---------------------------------------------------------------------------

_PROFANE_WORDS = {
    "ass", "asshole", "bastard", "bitch", "bullshit", "cock", "crap", "cunt",
    "damn", "dick", "douchebag", "fag", "faggot", "fuck", "fucker", "fucking",
    "goddamn", "hell", "jackass", "motherfucker", "nigger", "nigga", "penis",
    "piss", "prick", "pussy", "shit", "shitty", "slut", "twat", "vagina",
    "whore", "wanker", "retard", "retarded",
}


def _contains_profanity(text: str) -> bool:
    # Word-boundary match only — substring matching produced false positives
    # like "hello" → "hell" or "class" → "ass".
    normalized = _re.sub(r"[^a-z]", " ", text.lower())
    words = normalized.split()
    return any(w in _PROFANE_WORDS for w in words)



# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CreateAccount(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    mystery: str = Field(..., min_length=1)


class EvidenceItemModel(BaseModel):
    field_order: int = Field(..., ge=1, le=MAX_EVIDENCE)
    type: str = Field(..., pattern="^(text|image|csv)$")
    content: str = Field(default="", max_length=MAX_EVIDENCE_ITEM_BYTES)


class CreateSubmission(BaseModel):
    account_id: str
    solution: str = Field(default="", max_length=MAX_TEXT_FIELD_LEN)
    recommendation: str = Field(default="", max_length=MAX_TEXT_FIELD_LEN)
    evidence: list[EvidenceItemModel] = []


# ---------------------------------------------------------------------------
# Background provisioning
# ---------------------------------------------------------------------------

def _run_provisioning(account_id: str, mystery: str):
    """Run provisioning in a background thread."""
    scenario = SCENARIOS.get(mystery)
    if not scenario:
        _set_provisioning_status(account_id, {
            "step": "error",
            "message": f"Unknown scenario: {mystery}",
            "progress": 0,
            "total": TOTAL_STEPS,
            "error": True,
        })
        return

    def progress_callback(step: str, message: str, progress: int, total: int):
        status = {
            "step": step,
            "message": message,
            "progress": progress,
            "total": total,
        }
        _set_provisioning_status(account_id, status)

    try:
        result = provision_scenario(scenario["key"], progress_callback)

        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            # Update the account with the Genie URL
            conn.execute(
                "UPDATE accounts SET genie_url = ? WHERE id = ?",
                (result["genie_url"], account_id),
            )
            # Record in provisioned_spaces (for future idempotency)
            conn.execute("""
                INSERT OR REPLACE INTO provisioned_spaces
                (scenario, catalog_name, genie_space_id, genie_url, provisioned_at, provisioned_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (mystery, result["catalog_name"], result["genie_space_id"],
                  result["genie_url"], now, account_id))

        _set_provisioning_status(account_id, {
            "step": "done",
            "message": "Your case is ready!",
            "progress": TOTAL_STEPS,
            "total": TOTAL_STEPS,
            "genie_url": result["genie_url"],
        })

    except Exception as e:
        log.exception(f"Provisioning failed for {account_id}")
        _set_provisioning_status(account_id, {
            "step": "error",
            "message": "Provisioning failed. Check the app logs for details.",
            "progress": 0,
            "total": TOTAL_STEPS,
            "error": True,
        })


# ---------------------------------------------------------------------------
# API sub-application
# ---------------------------------------------------------------------------

api = FastAPI()


# -- Config -----------------------------------------------------------------

@api.get("/config")
def get_config():
    """Return non-sensitive workspace info for the frontend."""
    host = os.environ.get("DATABRICKS_HOST", "")
    if host and not host.startswith("http"):
        host = f"https://{host}"
    return {
        "workspace_host": host,
        "leaderboard_form_url": LEADERBOARD_FORM_URL,
    }


# -- Accounts ---------------------------------------------------------------

@api.post("/accounts")
def create_account(body: CreateAccount):
    if _contains_profanity(body.nickname):
        raise HTTPException(400, "Nickname contains inappropriate language. Please choose another.")
    if body.mystery not in MYSTERIES:
        raise HTTPException(400, f"Invalid mystery. Choose one of: {', '.join(MYSTERIES)}")

    account_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Check if this scenario is already provisioned on this workspace
    with get_db() as conn:
        existing = conn.execute(
            "SELECT genie_url FROM provisioned_spaces WHERE scenario = ?",
            (body.mystery,),
        ).fetchone()

    genie_url = existing["genie_url"] if existing else ""
    provisioning_status = "completed" if existing else "pending"

    with get_db() as conn:
        conn.execute(
            "INSERT INTO accounts (id, nickname, mystery, genie_url, created_at) VALUES (?, ?, ?, ?, ?)",
            (account_id, body.nickname.strip(), body.mystery, genie_url, now),
        )

    # Start background provisioning if needed
    if not existing:
        _set_provisioning_status(account_id, {
            "step": "pending",
            "message": "Preparing your investigation...",
            "progress": 0,
            "total": TOTAL_STEPS,
        })
        t = threading.Thread(target=_run_provisioning, args=(account_id, body.mystery), daemon=True)
        t.start()

    return {
        "id": account_id,
        "nickname": body.nickname.strip(),
        "mystery": body.mystery,
        "provisioning_status": provisioning_status,
        "genie_url": genie_url or None,
        "created_at": now,
    }


@api.get("/accounts/{account_id}")
def get_account(account_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, nickname, mystery, genie_url, created_at FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Account not found")
    result = dict(row)
    # Prefer the latest URL from provisioned_spaces (updated on each startup)
    with get_db() as conn:
        ps = conn.execute(
            "SELECT genie_url FROM provisioned_spaces WHERE scenario = ?",
            (result["mystery"],),
        ).fetchone()
    if ps and ps["genie_url"]:
        result["genie_url"] = ps["genie_url"]
    return result


# -- Provisioning status (SSE) ---------------------------------------------

@api.get("/provisioning/{account_id}/status")
def provisioning_status_sse(account_id: str):
    """Server-Sent Events stream for provisioning progress."""
    def event_stream():
        last_step = None
        timeout = 300  # 5 minute max
        elapsed = 0
        while elapsed < timeout:
            status = _get_provisioning_status(account_id)
            if status and status.get("step") != last_step:
                last_step = status["step"]
                yield f"data: {json.dumps(status)}\n\n"
                if status.get("step") in ("done", "error"):
                    return
            _time.sleep(1)
            elapsed += 1
        last = _get_provisioning_status(account_id) or {}
        timeout_event = {
            "step": "error",
            "message": "Provisioning timed out",
            "progress": last.get("progress", 0),
            "total": last.get("total", TOTAL_STEPS),
            "error": True,
        }
        yield f"data: {json.dumps(timeout_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# -- Provisioning status (polling fallback) ---------------------------------

@api.get("/provisioning/{account_id}/poll")
def provisioning_status_poll(account_id: str):
    """Polling fallback for provisioning status."""
    status = _get_provisioning_status(account_id)
    if not status:
        # Check if already provisioned in DB
        with get_db() as conn:
            acct = conn.execute(
                "SELECT genie_url FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        if acct and acct["genie_url"]:
            return {
                "step": "done",
                "message": "Your case is ready!",
                "progress": 8,
                "total": TOTAL_STEPS,
                "genie_url": acct["genie_url"],
            }
        raise HTTPException(404, "No provisioning status found")
    return status


# -- Submissions ------------------------------------------------------------

@api.post("/submissions")
def create_submission(body: CreateSubmission):
    with get_db() as conn:
        acct = conn.execute("SELECT id, mystery FROM accounts WHERE id = ?",
                            (body.account_id,)).fetchone()
        if not acct:
            raise HTTPException(404, "Account not found")

        if len(body.evidence) > MAX_EVIDENCE:
            raise HTTPException(400, f"Maximum {MAX_EVIDENCE} evidence fields allowed")

        total_evidence_bytes = sum(len(e.content) for e in body.evidence)
        if total_evidence_bytes > MAX_SUBMISSION_TOTAL_BYTES:
            raise HTTPException(
                413,
                f"Submission too large: {total_evidence_bytes} bytes "
                f"exceeds limit of {MAX_SUBMISSION_TOTAL_BYTES} bytes",
            )

        submission_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        mystery = acct["mystery"]

        # Preliminary score: evidence count only
        non_empty_evidence = [e for e in body.evidence if e.content.strip()][:SCORED_EVIDENCE]
        ev_score = len(non_empty_evidence) * POINTS_PER_EVIDENCE
        score = ev_score

        conn.execute(
            "INSERT INTO submissions (id, account_id, solution, recommendation, submitted_at, score, root_cause_score, evidence_score, recommendation_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (submission_id, body.account_id, body.solution, body.recommendation, now, score, 0, ev_score, 0),
        )
        for ev in body.evidence:
            conn.execute(
                "INSERT INTO evidence (id, submission_id, field_order, type, content) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), submission_id, ev.field_order, ev.type, ev.content),
            )

    # Score immediately (keyword-based, no LLM delay)
    rc_score = 0
    rec_score = 0
    if mystery in MYSTERY_ANSWER_KEYS:
        answer_key = MYSTERY_ANSWER_KEYS[mystery]
        rc_score = _score_root_cause(body.solution, answer_key["root_cause"])
        rec_score = _score_recommendation(body.recommendation, answer_key["root_cause"], answer_key["scoring_context"])

    total = rc_score + ev_score + rec_score
    with get_db() as conn2:
        conn2.execute(
            "UPDATE submissions SET score = ?, root_cause_score = ?, evidence_score = ?, recommendation_score = ? WHERE id = ?",
            (total, rc_score, ev_score, rec_score, submission_id),
        )

    return {
        "id": submission_id,
        "score": total,
        "root_cause_score": rc_score,
        "evidence_score": ev_score,
        "recommendation_score": rec_score,
        "submitted_at": now,
    }


@api.get("/submissions/{account_id}")
def get_latest_submission(account_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, solution, recommendation, submitted_at, score, root_cause_score, evidence_score, recommendation_score FROM submissions WHERE account_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if not row:
            return None
        submission = dict(row)
        evidence_rows = conn.execute(
            "SELECT field_order, type, content FROM evidence WHERE submission_id = ? ORDER BY field_order",
            (submission["id"],),
        ).fetchall()
        submission["evidence"] = [dict(e) for e in evidence_rows]
    return submission


# -- Self-scoring -----------------------------------------------------------

@api.post("/score/{account_id}")
def score_submission(account_id: str):
    """Score the latest submission for this account."""
    with get_db() as conn:
        acct = conn.execute("SELECT mystery FROM accounts WHERE id = ?",
                            (account_id,)).fetchone()
        if not acct:
            raise HTTPException(404, "Account not found")

        mystery = acct["mystery"]
        if mystery not in MYSTERY_ANSWER_KEYS:
            raise HTTPException(400, "No answer key available for this mystery")

        answer_key = MYSTERY_ANSWER_KEYS[mystery]
        root_cause = answer_key["root_cause"]
        scoring_context = answer_key["scoring_context"]

        sub = conn.execute(
            "SELECT id, solution, recommendation FROM submissions WHERE account_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if not sub:
            raise HTTPException(400, "No submission found. Submit your answer first.")

        evidence_rows = conn.execute(
            "SELECT field_order, type, content FROM evidence WHERE submission_id = ? ORDER BY field_order",
            (sub["id"],),
        ).fetchall()

    # Score (keyword-based, instant)
    rc_score = _score_root_cause(sub["solution"], root_cause)
    ev_score = _score_evidence(evidence_rows)
    rec_score = _score_recommendation(sub["recommendation"], root_cause, scoring_context)
    total = rc_score + ev_score + rec_score

    with get_db() as conn:
        conn.execute(
            "UPDATE submissions SET score = ?, root_cause_score = ?, evidence_score = ?, recommendation_score = ? WHERE id = ?",
            (total, rc_score, ev_score, rec_score, sub["id"]),
        )

    return {
        "score": total,
        "root_cause_score": rc_score,
        "evidence_score": ev_score,
        "recommendation_score": rec_score,
    }


# -- Answer reveal ----------------------------------------------------------

@api.get("/answer/{mystery}")
def get_answer(mystery: str):
    """Return the correct answer for a mystery."""
    if mystery not in MYSTERY_ANSWER_KEYS:
        raise HTTPException(404, "Unknown mystery")

    key = MYSTERY_ANSWER_KEYS[mystery]
    return {
        "mystery": mystery,
        "root_cause": key["root_cause"],
        "sample_recommendation": key.get("sample_recommendation", ""),
        "query_path": key.get("query_path", []),
    }


# ---------------------------------------------------------------------------
# Startup: optional pre-provisioning
# ---------------------------------------------------------------------------

def _provision_all_at_startup():
    """Provision every scenario on app startup. Opt-in only (PRE_PROVISION_ALL)."""
    for mystery_name, scenario in SCENARIOS.items():
        key = scenario["key"]
        try:
            log.info(f"[startup] Provisioning {mystery_name}...")
            result = provision_scenario(key)
            now = datetime.now(timezone.utc).isoformat()
            with get_db() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO provisioned_spaces
                    (scenario, catalog_name, genie_space_id, genie_url, provisioned_at, provisioned_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (mystery_name, result["catalog_name"], result["genie_space_id"],
                      result["genie_url"], now, "startup"))
            log.info(f"[startup] {mystery_name} ready: {result['genie_url']}")
        except Exception as e:
            log.error(f"[startup] Failed to provision {mystery_name}: {e}")


@asynccontextmanager
async def lifespan(app):
    if PRE_PROVISION_ALL:
        log.info("PRE_PROVISION_ALL=true — pre-provisioning every scenario at startup")
        t = threading.Thread(target=_provision_all_at_startup, daemon=True)
        t.start()
    else:
        log.info("Default mode: scenarios are provisioned on-demand when a player picks one")
    yield


# ---------------------------------------------------------------------------
# Main application — mount API then static files
# ---------------------------------------------------------------------------

app = FastAPI(lifespan=lifespan)
app.mount("/api", api)

static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
