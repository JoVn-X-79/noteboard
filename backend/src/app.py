# Noteboard backend — Flask REST API
# Endpoints: GET/POST /api/notes, DELETE /api/notes/<id>, GET /api/health
# Connects to PostgreSQL using env vars: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify

app = Flask(__name__)


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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        conn.commit()


# ── Health probe ──────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"}), 200


# ── Notes CRUD ────────────────────────────────────────────────────────────────

@app.route("/api/notes", methods=["GET"])
def list_notes():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, text, created_at FROM notes ORDER BY created_at DESC")
            rows = cur.fetchall()
    return jsonify([dict(r) for r in rows]), 200


@app.route("/api/notes", methods=["POST"])
def create_note():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO notes (text) VALUES (%s) RETURNING id, text, created_at",
                (text,),
            )
            row = cur.fetchone()
        conn.commit()
    return jsonify(dict(row)), 201


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
