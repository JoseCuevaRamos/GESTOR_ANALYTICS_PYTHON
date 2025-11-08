from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.tarea import Tarea
from app.models.columna import Columna
from app.models.usuario_rol import UsuarioRol
from datetime import datetime, timedelta

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def format_time(seconds):
    """Convierte segundos a formato mm:ss"""
    if not seconds or seconds <= 0:
        return "0:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

@router.get("/proyectos/{id}/metricas")
def metricas_proyecto(id: int, db: Session = Depends(get_db)):
    print("\n" + "="*80)
    print(f"CALCULANDO MÉTRICAS PARA PROYECTO {id}")
    print("="*80)
    
    tareas = db.query(Tarea)\
        .join(Columna, Tarea.id_columna == Columna.id_columna)\
        .filter(
            Tarea.id_proyecto == id,
            Tarea.status == '0',
            Columna.status == '0'
        ).all()
    
    print(f"\nTareas filtradas (status='0'): {len(tareas)}")
    for t in tareas:
        print(f"  - ID: {t.id_tarea}, Título: {t.titulo}, Status: '{t.status}'")
    print(f"\nDEBUG QUERY: Buscando columnas donde id_proyecto={id} y status='0'")

    columnas = db.query(Columna)\
        .filter(Columna.id_proyecto == id, Columna.status == '0')\
        .all()

    # CREAR columnas_map AQUÍ (fuera del loop)
    columnas_map = {c.id_columna: c.status_fijas for c in columnas}
    
    print(f"🔍 RESULTADO: {len(columnas)} columnas encontradas")

    for c in columnas:
        print(f"  - ID: {c.id_columna}, Nombre: {c.nombre}, id_proyecto: {c.id_proyecto}, status_fijas: {c.status_fijas}")

    print(f"📋 Columnas mapeadas: {columnas_map}")

    # cycle_times AFUERA del loop
    cycle_times = []
    for t in tareas:
        if t.started_at and t.completed_at:
            diff_seconds = (t.completed_at - t.started_at).total_seconds()
            if diff_seconds > 0:
                cycle_times.append(diff_seconds)
    
    # Convertir a formato mm:ss
    if cycle_times:
        avg_cycle_time_seconds = sum(cycle_times) / len(cycle_times)
        avg_cycle_time_formatted = format_time(avg_cycle_time_seconds)
    else:
        avg_cycle_time_seconds = 0
        avg_cycle_time_formatted = "0:00"
    
    print(f"⏱️  Cycle Time: {len(cycle_times)} tareas, promedio {avg_cycle_time_formatted}")

    lead_times = []
    for t in tareas:
        if t.created_at and t.completed_at:
            diff_seconds = (t.completed_at - t.created_at).total_seconds()
            if diff_seconds > 0:
                lead_times.append(diff_seconds)
    
    # Convertir a formato mm:ss
    if lead_times:
        avg_lead_time_seconds = sum(lead_times) / len(lead_times)
        avg_lead_time_formatted = format_time(avg_lead_time_seconds)
    else:
        avg_lead_time_seconds = 0
        avg_lead_time_formatted = "0:00"
    
    print(f" Lead Time: {len(lead_times)} tareas, promedio {avg_lead_time_formatted}")

    tareas_completadas = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) == '2'
    ])
    
    tareas_en_progreso = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) == '1'
    ])
    
    tareas_pendientes = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) is None
    ])

    total_tareas = len(tareas)
    print(f"\nCONTEO: Completas={tareas_completadas}, Progreso={tareas_en_progreso}, Pendientes={tareas_pendientes}, Total={total_tareas}")

    entregas_a_tiempo = 0
    entregas_tarde = 0
    for t in tareas:
        if t.completed_at and t.due_at:
            if t.completed_at <= t.due_at:
                entregas_a_tiempo += 1
            else:
                entregas_tarde += 1

    tareas_asignadas = len([t for t in tareas if t.id_asignado is not None])

    fecha_inicio_velocidad = datetime.now() - timedelta(days=14)
    tareas_completadas_recientes = []
    for t in tareas:
        if (columnas_map.get(t.id_columna) == '2' and 
            t.completed_at and 
            t.completed_at >= fecha_inicio_velocidad):
            tareas_completadas_recientes.append(t)
    
    velocidad = round(len(tareas_completadas_recientes) / 14, 2) if len(tareas_completadas_recientes) > 0 else 0.0

    try:
        miembros_activos = db.query(func.count(func.distinct(UsuarioRol.id_usuario)))\
            .filter(
                UsuarioRol.id_proyecto == id,
                UsuarioRol.status == '0'
            ).scalar() or 0
    except Exception as e:
        miembros_activos = 0

    if total_tareas > 0:
        progreso_ponderado = (tareas_completadas * 1.0) + (tareas_en_progreso * 0.5)
        rendimiento_porcentaje = (progreso_ponderado / total_tareas) * 100
        rendimiento_porcentaje = min(max(round(rendimiento_porcentaje, 1), 0.0), 100.0)
    else:
        rendimiento_porcentaje = 0.0
    
    print(f"\n📈 Rendimiento: {rendimiento_porcentaje}%")
    print("="*80 + "\n")

    return {
        "cycle_time_promedio": avg_cycle_time_formatted,  
        "lead_time_promedio": avg_lead_time_formatted,    
        "tareas_completadas": tareas_completadas,
        "tareas_en_progreso": tareas_en_progreso,
        "tareas_pendientes": tareas_pendientes,
        "entregas_a_tiempo": entregas_a_tiempo,
        "entregas_tarde": entregas_tarde,
        "total_tareas": total_tareas,
        "tareas_asignadas": tareas_asignadas,
        "velocidad": velocidad,
        "miembros_activos": miembros_activos,
        "rendimiento_porcentaje": rendimiento_porcentaje
    }