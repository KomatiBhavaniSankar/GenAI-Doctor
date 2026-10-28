import logging
from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db import sb
import admin

log = logging.getLogger("doctor-sim")
app = FastAPI(title="Doctor GenAI Simulation")
app.include_router(admin.router)


class DoctorIn(BaseModel):
    name: str
    specialization: str
    hospital: str

class SessionIn(BaseModel):
    doctor_id: str
    tab: str
    story: str
    opening: str
    device: Optional[str] = None
    user_agent: Optional[str] = None
    screen: Optional[str] = None

class EventIn(BaseModel):
    session_id: Optional[str] = None
    doctor_id: Optional[str] = None
    page: Optional[str] = None
    event_type: str
    label: Optional[str] = None
    duration_ms: Optional[int] = None
    client_ts: Optional[str] = None

class EventBatch(BaseModel):
    events: list[EventIn]

class RecordIn(BaseModel):
    session_id: Optional[str] = None
    doctor_id: str
    patient_name: str
    items: list[Any]
    notes: str = ""
    payload: Optional[dict] = None


def one(res):
    if not res.data:
        raise HTTPException(500, "Database write failed")
    return res.data[0]

def insert_compat(table: str, row: dict | list, new_cols: tuple[str, ...]):
    """Insert, and if the DB has not had migrate.sql applied yet, retry without the new columns."""
    try:
        return sb.table(table).insert(row).execute()
    except Exception as exc:
        log.warning("%s insert failed (%s); retrying without %s. Run migrate.sql.", table, exc, new_cols)
        strip = lambda r: {k: v for k, v in r.items() if k not in new_cols}
        return sb.table(table).insert([strip(r) for r in row] if isinstance(row, list) else strip(row)).execute()

@app.post("/api/doctors")
def add_doctor(d: DoctorIn):
    return one(sb.table("doctors").insert(d.model_dump()).execute())

@app.post("/api/sessions")
def add_session(s: SessionIn):
    return one(insert_compat("sessions", s.model_dump(), ("device", "user_agent", "screen")))

@app.post("/api/events")
def add_events(b: EventBatch):
    if b.events:
        insert_compat("events", [e.model_dump() for e in b.events], ("client_ts",))
    return {"saved": len(b.events)}

@app.post("/api/records")
def add_record(r: RecordIn):
    return one(insert_compat("patient_records", r.model_dump(), ("payload",)))

@app.get("/api/records")
def list_records(doctor_id: str):
    res = (sb.table("patient_records").select("*").eq("doctor_id", doctor_id)
           .order("created_at", desc=True).execute())
    return res.data

@app.get("/api/stats/{session_id}")
def stats(session_id: str):
    return sb.table("page_stats").select("*").eq("session_id", session_id).execute().data

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/admin")
def admin_portal():
    return FileResponse("static/admin.html")

# run: uvicorn main:app --reload --port 8003
