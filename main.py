import json
import urllib.request
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Literal

app = FastAPI(
    title="SmartDesk AI",
    description="Intelligent IT Helpdesk and Ticket Management System",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "smartdesk.db"
HTML_FILE = BASE_DIR / "index.html"


class Ticket(BaseModel):
    title: str
    description: str
    priority: Literal["Low", "Medium", "High"] = "Medium"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
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


initialize_database()


@app.get("/")
def home():
    if not HTML_FILE.is_file():
        raise HTTPException(
            status_code=404,
            detail="index.html not found. Please create it in the project folder."
        )
    return FileResponse(HTML_FILE)


@app.get("/api")
def api_home():
    return {"message": "Welcome to SmartDesk AI API!"}


@app.post("/tickets", status_code=201)
def create_ticket(ticket: Ticket):
    title = ticket.title.strip()
    description = ticket.description.strip()

    if not title or not description:
        raise HTTPException(
            status_code=400,
            detail="Title and description cannot be empty."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tickets (title, description, priority)
            VALUES (?, ?, ?)
            """,
            (title, description, ticket.priority)
        )

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

        return {
            "message": "Ticket created successfully!",
            "ticket": dict(row)
        }


@app.get("/tickets")
def get_tickets():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM tickets ORDER BY id"
        ).fetchall()

        return [dict(row) for row in rows]


@app.put("/tickets/{ticket_id}")
def update_ticket_status(ticket_id: int, status: str):
    allowed_statuses = ["Open", "In Progress", "Resolved"]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid status",
                "allowed_statuses": allowed_statuses
            }
        )

    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (status, ticket_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,)
        ).fetchone()

        return {
            "message": "Ticket status updated successfully!",
            "ticket": dict(row)
        }
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
