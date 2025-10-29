"""
Archivo principal de la aplicación FastAPI.
Define el punto de entrada y un endpoint de prueba /health.
"""
from fastapi import FastAPI
from app.routers import proyectos
from app.routers import metricas

app = FastAPI()
app.include_router(proyectos.router)
app.include_router(metricas.router)

@app.get("/health")
def health_check():
    """Endpoint de prueba para verificar el estado de la API."""
    return {"status": "ok"}
