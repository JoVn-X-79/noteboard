# Noteboard backend v2 — Flask REST API
# New in v2: color, pinned fields; PUT edit; PATCH pin toggle; GET ?q= search
# Connects to PostgreSQL via env vars: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify

app = Flask(__name__)

VALID_COLORS = {"yellow", "green", "blue", "pink", "purple", "orange"}


def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Create table if it doesn't exist (v1 compatible)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id         SERIAL PRIMARY KEY,
                    text       TEXT NOT NULL,
                    color      VARCHAR(20) DEFAULT 'yellow',
                    pinned     BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            # Migrate v1 tables: add columns if missing
            cur.execute("""
                ALTER TABLE notes
                    ADD COLUMN IF NOT EXISTS color      VARCHAR(20) DEFAULT 'yellow',
                    ADD COLUMN IF NOT EXISTS pinned     BOOLEAN     DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
            """)
        conn.commit()


# ── Health ────────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"}), 200


# ── Notes ─────────────────────────────────────────────────────────────────────

@app.route("/api/notes", methods=["GET"])
def list_notes():
    """List notes. Optional ?q= for full-text search. Pinned notes come first."""
    q = request.args.get("q", "").strip()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if q:
                cur.execute(
                    """SELECT id, text, color, pinned, created_at, updated_at
                       FROM notes
                       WHERE text ILIKE %s
                       ORDER BY pinned DESC, updated_at DESC""",
                    (f"%{q}%",),
                )
            else:
                cur.execute(
                    """SELECT id, text, color, pinned, created_at, updated_at
                       FROM notes
                       ORDER BY pinned DESC, updated_at DESC"""
                )
            rows = cur.fetchall()
    return jsonify([dict(r) for r in rows]), 200


@app.route("/api/notes", methods=["POST"])
def create_note():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    color = body.get("color", "yellow")
    if not text:
        return jsonify({"error": "text is required"}), 400
    if color not in VALID_COLORS:
        color = "yellow"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO notes (text, color)
                   VALUES (%s, %s)
                   RETURNING id, text, color, pinned, created_at, updated_at""",
                (text, color),
            )
            row = cur.fetchone()
        conn.commit()
    return jsonify(dict(row)), 201


@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    """Update text and/or color of an existing note."""
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    color = body.get("color")
    if not text:
        return jsonify({"error": "text is required"}), 400
    if color and color not in VALID_COLORS:
        color = "yellow"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if color:
                cur.execute(
                    """UPDATE notes SET text=%s, color=%s, updated_at=NOW()
                       WHERE id=%s
                       RETURNING id, text, color, pinned, created_at, updated_at""",
                    (text, color, note_id),
                )
            else:
                cur.execute(
                    """UPDATE notes SET text=%s, updated_at=NOW()
                       WHERE id=%s
                       RETURNING id, text, color, pinned, created_at, updated_at""",
                    (text, note_id),
                )
            row = cur.fetchone()
        conn.commit()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row)), 200


@app.route("/api/notes/<int:note_id>/pin", methods=["PATCH"])
def toggle_pin(note_id):
    """Toggle the pinned status of a note."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE notes SET pinned = NOT pinned, updated_at=NOW()
                   WHERE id=%s
                   RETURNING id, text, color, pinned, created_at, updated_at""",
                (note_id,),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row)), 200


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
            if cur.rowcount == 0:
                return jsonify({"error": "not found"}), 404
        conn.commit()
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
