"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import sqlite3
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DATABASE_PATH = current_dir / "activities.db"

INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    if not DATABASE_PATH.exists():
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                UNIQUE(activity_name, email),
                FOREIGN KEY(activity_name) REFERENCES activities(name) ON DELETE CASCADE
            )
            """
        )

        for activity_name, details in INITIAL_ACTIVITIES.items():
            conn.execute(
                "INSERT OR IGNORE INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                (activity_name, details["description"], details["schedule"], details["max_participants"])
            )
            for email in details["participants"]:
                conn.execute(
                    "INSERT OR IGNORE INTO participants (activity_name, email) VALUES (?, ?)",
                    (activity_name, email)
                )
    conn.close()


def load_activities():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT
            a.name,
            a.description,
            a.schedule,
            a.max_participants,
            GROUP_CONCAT(p.email) AS participants
        FROM activities a
        LEFT JOIN participants p ON a.name = p.activity_name
        GROUP BY a.name
        ORDER BY a.name
        """
    ).fetchall()
    conn.close()

    activities = {}
    for row in rows:
        participants = row["participants"].split(",") if row["participants"] else []
        activities[row["name"]] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": participants
        }

    return activities


initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    conn = get_db_connection()
    activity = conn.execute(
        "SELECT name, max_participants FROM activities WHERE name = ?",
        (activity_name,)
    ).fetchone()

    if not activity:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    current_count = conn.execute(
        "SELECT COUNT(*) FROM participants WHERE activity_name = ?",
        (activity_name,)
    ).fetchone()[0]

    if current_count >= activity["max_participants"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Activity is full")

    already_signed_up = conn.execute(
        "SELECT 1 FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email)
    ).fetchone()

    if already_signed_up:
        conn.close()
        raise HTTPException(status_code=400, detail="Student is already signed up")

    with conn:
        conn.execute(
            "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
            (activity_name, email)
        )

    conn.close()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    conn = get_db_connection()
    activity = conn.execute(
        "SELECT name FROM activities WHERE name = ?",
        (activity_name,)
    ).fetchone()

    if not activity:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    participant = conn.execute(
        "SELECT id FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email)
    ).fetchone()

    if not participant:
        conn.close()
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    with conn:
        conn.execute(
            "DELETE FROM participants WHERE id = ?",
            (participant["id"],)
        )

    conn.close()
    return {"message": f"Unregistered {email} from {activity_name}"}
