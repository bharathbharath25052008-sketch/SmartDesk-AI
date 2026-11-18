
import json
import sqlite3
import urllib.request
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="SmartDesk AI",
    description="Professional IT Helpdesk and Ticket Management System",
    version="2.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "smartdesk.db"
HTML_FILE = BASE_DIR / "index.html"

Priority = Literal["Low", "Medium", "High"]
Status = Literal["Open", "In Progress", "Resolved", "Closed"]


# -------------------- REQUEST MODELS --------------------

class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    priority: Priority = "Medium"


class TicketStatusUpdate(BaseModel):
    status: Status


class TicketEdit(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    priority: Optional[Priority] = None


class SettingsUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, max_length=100)
    administrator: Optional[str] = Field(default=None, max_length=100)
    team_name: Optional[str] = Field(default=None, max_length=100)


# -------------------- DATABASE --------------------

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Open'
            )
        """)

        # Safely add timestamp columns to an existing database.
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(tickets)")
        }

        if "created_at" not in columns:
            connection.execute("ALTER TABLE tickets ADD COLUMN created_at TEXT")

        if "updated_at" not in columns:
            connection.execute("ALTER TABLE tickets ADD COLUMN updated_at TEXT")

        connection.execute("""
            UPDATE tickets
            SET created_at = COALESCE(created_at, datetime('now')),
                updated_at = COALESCE(updated_at, datetime('now'))
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)

        defaults = {
            "company_name": "SmartDesk AI",
            "administrator": "Administrator",
            "team_name": "IT Support Team"
        }

        for key, value in defaults.items():
            connection.execute("""
                INSERT OR IGNORE INTO app_settings (setting_key, setting_value)
                VALUES (?, ?)
            """, (key, value))


initialize_database()


def get_ticket_or_404(connection, ticket_id: int):
    row = connection.execute(
        "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return dict(row)


# -------------------- DASHBOARD --------------------

@app.get("/")
def home():
    if not HTML_FILE.is_file():
        raise HTTPException(
            status_code=404,
            detail="index.html not found in the project folder."
        )
    return FileResponse(HTML_FILE)


@app.get("/api")
def api_home():
    return {
        "message": "Welcome to SmartDesk AI API!",
        "version": "2.0.0"
    }


# -------------------- TICKET CRUD --------------------

@app.post("/tickets", status_code=201)
def create_ticket(ticket: TicketCreate):
    title = ticket.title.strip()
    description = ticket.description.strip()

    if not title or not description:
        raise HTTPException(
            status_code=400,
            detail="Title and description cannot be empty."
        )

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tickets
                (title, description, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, 'Open', datetime('now'), datetime('now'))
        """, (title, description, ticket.priority))

        created = get_ticket_or_404(connection, cursor.lastrowid)

    return {
        "message": "Ticket created successfully!",
        "ticket": created
    }


@app.get("/tickets")
def get_tickets(
    search: Optional[str] = Query(default=None, max_length=200),
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    sql = "SELECT * FROM tickets WHERE 1=1"
    parameters = []

    if search and search.strip():
        term = f"%{search.strip()}%"
        sql += " AND (title LIKE ? OR description LIKE ? OR CAST(id AS TEXT) LIKE ?)"
        parameters.extend([term, term, term])

    if status and status != "All":
        if status == "Resolved":
            sql += " AND status IN ('Resolved', 'Closed')"
        else:
            sql += " AND status = ?"
            parameters.append(status)

    if priority and priority != "All":
        sql += " AND priority = ?"
        parameters.append(priority)

    sql += " ORDER BY id DESC"

    with get_connection() as connection:
        rows = connection.execute(sql, parameters).fetchall()

    return [dict(row) for row in rows]


@app.put("/tickets/{ticket_id}")
def update_ticket_status(ticket_id: int, payload: TicketStatusUpdate):
    with get_connection() as connection:
        get_ticket_or_404(connection, ticket_id)

        connection.execute("""
            UPDATE tickets
            SET status = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (payload.status, ticket_id))

        updated = get_ticket_or_404(connection, ticket_id)

    return {
        "message": "Ticket status updated successfully!",
        "ticket": updated
    }


@app.patch("/tickets/{ticket_id}")
def edit_ticket(ticket_id: int, payload: TicketEdit):
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update."
        )

    for key, value in changes.items():
        if isinstance(value, str) and not value.strip():
            raise HTTPException(
                status_code=400,
                detail=f"{key} cannot be empty."
            )

    allowed_fields = {"title", "description", "priority"}
    if not set(changes).issubset(allowed_fields):
        raise HTTPException(status_code=400, detail="Invalid update fields.")

    with get_connection() as connection:
        get_ticket_or_404(connection, ticket_id)

        assignments = ", ".join(f"{key} = ?" for key in changes)
        values = [value.strip() if isinstance(value, str) else value
                  for value in changes.values()]

        connection.execute(
            f"""
            UPDATE tickets
            SET {assignments}, updated_at = datetime('now')
            WHERE id = ?
            """,
            values + [ticket_id]
        )

        updated = get_ticket_or_404(connection, ticket_id)

    return {
        "message": "Ticket updated successfully!",
        "ticket": updated
    }


@app.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: int):
    with get_connection() as connection:
        get_ticket_or_404(connection, ticket_id)
        connection.execute(
            "DELETE FROM tickets WHERE id = ?", (ticket_id,)
        )

    return {"message": "Ticket deleted successfully!", "ticket_id": ticket_id}


# -------------------- DASHBOARD ANALYTICS --------------------

@app.get("/analytics")
def get_analytics():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved,
                SUM(CASE WHEN priority = 'High' THEN 1 ELSE 0 END) AS high_priority,
                SUM(CASE WHEN priority = 'Medium' THEN 1 ELSE 0 END) AS medium_priority,
                SUM(CASE WHEN priority = 'Low' THEN 1 ELSE 0 END) AS low_priority
            FROM tickets
        """).fetchone()

        recent = connection.execute("""
            SELECT * FROM tickets ORDER BY id DESC LIMIT 5
        """).fetchall()

    stats = {
        key: row_value or 0
        for key, row_value in dict(rows).items()
    }

    total = stats["total"]

    return {
        "total": total,
        "open": stats["open"],
        "in_progress": stats["in_progress"],
        "resolved": stats["resolved"],
        "high_priority": stats["high_priority"],
        "medium_priority": stats["medium_priority"],
        "low_priority": stats["low_priority"],
        "open_percentage": round(stats["open"] * 100 / total) if total else 0,
        "in_progress_percentage": round(stats["in_progress"] * 100 / total) if total else 0,
        "resolved_percentage": round(stats["resolved"] * 100 / total) if total else 0,
        "recent_tickets": [dict(ticket) for ticket in recent]
    }


# -------------------- SETTINGS --------------------

@app.get("/settings")
def get_settings():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT setting_key, setting_value FROM app_settings"
        ).fetchall()

    return {row["setting_key"]: row["setting_value"] for row in rows}


@app.put("/settings")
def update_settings(payload: SettingsUpdate):
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No settings provided.")

    with get_connection() as connection:
        for key, value in changes.items():
            if value is None or not value.strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"{key} cannot be empty."
                )

            connection.execute("""
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key)
                DO UPDATE SET setting_value = excluded.setting_value
            """, (key, value.strip()))

    return {
        "message": "Settings saved successfully!",
        "settings": get_settings()
    }


# -------------------- LOCAL AI TROUBLESHOOTING --------------------

@app.post("/ai/troubleshoot")
def ai_troubleshoot(data: dict):
    issue = str(data.get("issue", "")).strip()

    if not issue:
        raise HTTPException(
            status_code=400,
            detail="Please describe your IT problem."
        )

    prompt = (
        "You are SmartDesk AI, a professional IT support assistant. "
        "Analyze this IT issue: " + issue +
        ". Give likely causes, step-by-step troubleshooting, "
        "and prevention tips. Use simple, safe instructions."
    )

    payload = json.dumps({
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        return {
            "issue": issue,
            "ai_response": result.get(
                "response", "No response received from AI."
            )
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local AI is unavailable. Check whether Ollama is running. "
                + str(error)
            )
        )
