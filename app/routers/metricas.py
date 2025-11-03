from fastapi import APIRouter, Depends, Query
from app.core.auth import get_current_user
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.tarea import Tarea
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/proyectos/{id}/metricas")
def metricas_proyecto(id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    tareas = db.query(Tarea).filter(Tarea.id_proyecto == id).all()

    # Cycle Time (en minutos)
    cycle_times = [ (t.completed_at - t.started_at).total_seconds() / 60 for t in tareas if t.started_at and t.completed_at ]
    avg_cycle_time = int(sum(cycle_times) / len(cycle_times)) if cycle_times else 0

    # Lead Time (en minutos)
    lead_times = [ (t.completed_at - t.created_at).total_seconds() / 60 for t in tareas if t.created_at and t.completed_at ]
    avg_lead_time = int(sum(lead_times) / len(lead_times)) if lead_times else 0

    # Tareas completadas
    tareas_completadas = len([t for t in tareas if t.completed_at])

    # Tareas en progreso
    tareas_en_progreso = len([t for t in tareas if t.started_at and not t.completed_at])

    # Tareas pendientes
    tareas_pendientes = len([t for t in tareas if not t.started_at and not t.completed_at])


    # Entregas a tiempo/tarde
    entregas_a_tiempo = 0
    entregas_tarde = 0
    for t in tareas:
        if t.completed_at and t.due_at:
            if t.completed_at <= t.due_at:
                entregas_a_tiempo += 1
            else:
                entregas_tarde += 1

    return {
        "cycle_time_promedio": avg_cycle_time,
        "lead_time_promedio": avg_lead_time,
        "tareas_completadas": tareas_completadas,
        "tareas_en_progreso": tareas_en_progreso,
        "tareas_pendientes": tareas_pendientes,
        "entregas_a_tiempo": entregas_a_tiempo,
        "entregas_tarde": entregas_tarde
    }
