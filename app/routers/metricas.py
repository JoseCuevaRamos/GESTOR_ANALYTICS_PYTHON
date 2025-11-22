from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.tarea import Tarea
from app.models.columna import Columna
from app.models.usuario_rol import UsuarioRol
from app.models.historial_movimiento import HistorialMovimiento
from app.core.auth import get_current_user
from datetime import datetime, timedelta, date
from typing import Dict, List

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/proyectos/{id}/metricas")
def metricas_proyecto(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Endpoint para obtener las métricas generales del proyecto.
    Tiempos calculados en DÍAS con 2 decimales.
    """
    print(f"\n{'='*60}")
    print(f"🔍 CALCULANDO MÉTRICAS PARA PROYECTO {id}")
    print(f"{'='*60}")

    def _is_project_leader(user_obj, proyecto_id, db_session: Session):
        try:
            user_id = user_obj.id_usuario if hasattr(user_obj, 'id_usuario') else int(user_obj)
        except Exception:
            return False
        rol = db_session.query(UsuarioRol).filter(
            UsuarioRol.id_proyecto == proyecto_id,
            UsuarioRol.id_usuario == user_id,
            UsuarioRol.id_rol == 1,
            UsuarioRol.status == '0'
        ).first()
        return rol is not None

    if not _is_project_leader(current_user, id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere ser líder del proyecto para acceder a esta ruta")
    
    # Filtrar tareas activas del proyecto
    tareas = db.query(Tarea)\
        .join(Columna, Tarea.id_columna == Columna.id_columna)\
        .filter(
            Tarea.id_proyecto == id,
            Tarea.status == '0',
            Columna.status == '0'
        ).all()

    print(f"📋 Total de tareas activas encontradas: {len(tareas)}")

    # Filtrar columnas del proyecto
    try:
        columnas = db.query(Columna).filter(
            Columna.status == '0',
            Columna.id_proyecto == id
        ).all()
        columnas_map = {c.id_columna: c.status_fijas for c in columnas}
        print(f"📊 Columnas del proyecto: {len(columnas)}")
        for col in columnas:
            print(f"   - Col {col.id_columna}: {col.nombre} (status_fijas={col.status_fijas})")
    except Exception as e:
        print(f"❌ Error al cargar columnas: {e}")
        columnas_map = {}

    # ✅ Cycle Time en DÍAS
    print(f"\n⏱️  CALCULANDO CYCLE TIME...")
    cycle_times = []
    for t in tareas:
        if t.started_at and t.completed_at:
            delta_seconds = (t.completed_at - t.started_at).total_seconds()
            dias = delta_seconds / (60 * 60 * 24)
            cycle_times.append(dias)
            print(f"   Tarea {t.id_tarea}: {t.started_at} → {t.completed_at} = {dias:.2f} días")
        elif t.started_at:
            print(f"   Tarea {t.id_tarea}: started_at OK pero completed_at es NULL")
        elif t.completed_at:
            print(f"   Tarea {t.id_tarea}: completed_at OK pero started_at es NULL")
    
    avg_cycle_time = round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else 0.0
    print(f"✅ Cycle Time Promedio: {avg_cycle_time} días ({len(cycle_times)} tareas con datos)")

    # ✅ Lead Time en DÍAS
    print(f"\n⏱️  CALCULANDO LEAD TIME...")
    lead_times = []
    for t in tareas:
        if t.created_at and t.completed_at:
            delta_seconds = (t.completed_at - t.created_at).total_seconds()
            dias = delta_seconds / (60 * 60 * 24)
            lead_times.append(dias)
            print(f"   Tarea {t.id_tarea}: {t.created_at} → {t.completed_at} = {dias:.2f} días")
        elif not t.completed_at:
            print(f"   Tarea {t.id_tarea}: NO completada (completed_at es NULL)")
    
    avg_lead_time = round(sum(lead_times) / len(lead_times), 2) if lead_times else 0.0
    print(f"✅ Lead Time Promedio: {avg_lead_time} días ({len(lead_times)} tareas con datos)")

    # Clasificación basada en columna.status_fijas
    print(f"\n📊 CLASIFICACIÓN DE TAREAS...")
    tareas_completadas = len([t for t in tareas if columnas_map.get(t.id_columna) == '2'])
    tareas_en_progreso = len([t for t in tareas if columnas_map.get(t.id_columna) == '1'])
    tareas_pendientes = len([t for t in tareas if columnas_map.get(t.id_columna) is None])
    
    print(f"   ✅ Completadas (status_fijas='2'): {tareas_completadas}")
    print(f"   🔄 En Progreso (status_fijas='1'): {tareas_en_progreso}")
    print(f"   ⏳ Pendientes (status_fijas=NULL): {tareas_pendientes}")

    # Validación de consistencia
    total_tareas = len(tareas)
    suma_verificacion = tareas_completadas + tareas_en_progreso + tareas_pendientes
    
    if suma_verificacion != total_tareas:
        print(f"⚠️  INCONSISTENCIA: {tareas_completadas} + {tareas_en_progreso} + {tareas_pendientes} = {suma_verificacion} != {total_tareas}")
        tareas_pendientes = max(0, total_tareas - tareas_completadas - tareas_en_progreso)
        print(f"   Ajustando pendientes a: {tareas_pendientes}")

    # ✅ Entregas a tiempo/tarde
    print(f"\n📅 CALCULANDO ENTREGAS A TIEMPO/TARDE...")
    entregas_a_tiempo = 0
    entregas_tarde = 0
    tareas_con_fecha_limite = 0
    
    for t in tareas:
        if t.completed_at and t.due_at:
            tareas_con_fecha_limite += 1
            if t.completed_at <= t.due_at:
                entregas_a_tiempo += 1
                print(f"   ✅ Tarea {t.id_tarea}: A TIEMPO (completada {t.completed_at} <= límite {t.due_at})")
            else:
                entregas_tarde += 1
                diferencia = (t.completed_at - t.due_at).total_seconds() / (60 * 60 * 24)
                print(f"   ⏰ Tarea {t.id_tarea}: TARDE (completada {t.completed_at} > límite {t.due_at}) +{diferencia:.1f} días")
        else:
            razon = []
            if not t.completed_at:
                razon.append("completed_at=NULL")
            if not t.due_at:
                razon.append("due_at=NULL")
            print(f"   ⊘  Tarea {t.id_tarea}: SIN DATOS ({', '.join(razon)})")
    
    print(f"✅ Entregas a tiempo: {entregas_a_tiempo}")
    print(f"⏰ Entregas tarde: {entregas_tarde}")
    print(f"📊 Total tareas con fecha límite: {tareas_con_fecha_limite}")

    # Tareas asignadas
    tareas_asignadas = len([t for t in tareas if t.id_asignado is not None])
    print(f"\n👥 Tareas asignadas: {tareas_asignadas}/{total_tareas}")

    # Velocidad
    fecha_inicio_velocidad = datetime.now() - timedelta(days=14)
    tareas_completadas_recientes = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) == '2'
        and t.completed_at
        and t.completed_at >= fecha_inicio_velocidad
    ])
    velocidad = round(tareas_completadas_recientes / 14, 2) if tareas_completadas_recientes > 0 else 0.0
    print(f"⚡ Velocidad: {velocidad} tareas/día (últimos 14 días: {tareas_completadas_recientes} tareas)")

    # Miembros activos
    try:
        miembros_activos = db.query(func.count(func.distinct(UsuarioRol.id_usuario)))\
            .filter(
                UsuarioRol.id_proyecto == id,
                UsuarioRol.status == '0'
            ).scalar() or 0
        print(f"👥 Miembros activos: {miembros_activos}")
    except Exception as e:
        print(f"⚠️  Error al contar miembros: {e}")
        miembros_activos = 0

    # Rendimiento del equipo
    if total_tareas > 0:
        progreso_ponderado = (tareas_completadas * 1.0) + (tareas_en_progreso * 0.5)
        rendimiento_porcentaje = (progreso_ponderado / total_tareas) * 100
        rendimiento_porcentaje = min(max(round(rendimiento_porcentaje, 1), 0.0), 100.0)
    else:
        rendimiento_porcentaje = 0.0
    
    print(f"📊 Rendimiento del equipo: {rendimiento_porcentaje}%")
    print(f"{'='*60}\n")

    return {
        "cycle_time_promedio": avg_cycle_time,
        "lead_time_promedio": avg_lead_time,
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


@router.get("/proyectos/{id_proyecto}/cfd")
def cfd_proyecto(
    id_proyecto: int,
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Endpoint para obtener los datos del Cumulative Flow Diagram (CFD).
    Solo accesible para usuarios con rol de líder (id_rol == 1) en el proyecto.
    """
    def _is_project_leader(user_obj, proyecto_id, db_session: Session):
        try:
            user_id = user_obj.id_usuario if hasattr(user_obj, 'id_usuario') else int(user_obj)
        except Exception:
            return False
        rol = db_session.query(UsuarioRol).filter(
            UsuarioRol.id_proyecto == proyecto_id,
            UsuarioRol.id_usuario == user_id,
            UsuarioRol.id_rol == 1,
            UsuarioRol.status == '0'
        ).first()
        return rol is not None

    if not _is_project_leader(current_user, id_proyecto, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere ser líder del proyecto para acceder al CFD",
        )

    hoy = datetime.now().date()

    try:
        to_dt: date = datetime.strptime(to_date, "%Y-%m-%d").date() if to_date else hoy
    except ValueError:
        raise HTTPException(status_code=400, detail="Parámetro 'to' inválido, formato YYYY-MM-DD")

    try:
        from_dt: date = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else to_dt
    except ValueError:
        raise HTTPException(status_code=400, detail="Parámetro 'from' inválido, formato YYYY-MM-DD")

    if from_dt > to_dt:
        raise HTTPException(status_code=400, detail="'from' no puede ser mayor que 'to'")

    columnas: List[Columna] = (
        db.query(Columna)
        .filter(
            Columna.status == '0',
            Columna.id_proyecto == id_proyecto
        )
        .order_by(Columna.posicion, Columna.id_columna)
        .all()
    )

    print(f"📊 CFD - Proyecto {id_proyecto}: {len(columnas)} columnas")

    base_conteos: Dict[str, int] = {str(c.id_columna): 0 for c in columnas}

    tareas_proyecto: List[Tarea] = (
        db.query(Tarea)
        .filter(
            Tarea.id_proyecto == id_proyecto,
            Tarea.status == '0'
        )
        .all()
    )

    print(f"📋 CFD - Proyecto {id_proyecto}: {len(tareas_proyecto)} tareas")

    data: List[Dict] = []
    dia_actual = from_dt

    while dia_actual <= to_dt:
        fin_dia = datetime.combine(dia_actual, datetime.max.time())
        conteos = dict(base_conteos)

        tareas_en_rango = [
            t for t in tareas_proyecto
            if t.created_at is None or t.created_at <= fin_dia
        ]

        for tarea in tareas_en_rango:
            movimiento: HistorialMovimiento | None = (
                db.query(HistorialMovimiento)
                .filter(
                    HistorialMovimiento.id_tarea == tarea.id_tarea,
                    HistorialMovimiento.timestamp <= fin_dia,
                )
                .order_by(HistorialMovimiento.timestamp.desc())
                .first()
            )

            if movimiento:
                id_columna_final = movimiento.id_columna_nueva
            else:
                id_columna_final = tarea.id_columna

            if id_columna_final is None:
                continue

            key = str(id_columna_final)
            if key in conteos:
                conteos[key] += 1

        data.append({
            "date": dia_actual.strftime("%Y-%m-%d"),
            "counts": conteos,
        })

        dia_actual += timedelta(days=1)

    columns_response = [
        {"id": c.id_columna, "name": c.nombre} 
        for c in columnas
    ]

    print(f"✅ CFD generado: {len(data)} días, {len(columns_response)} columnas")

    return {
        "proyecto_id": id_proyecto,
        "from": from_dt.strftime("%Y-%m-%d"),
        "to": to_dt.strftime("%Y-%m-%d"),
        "columns": columns_response,
        "data": data,
    }
