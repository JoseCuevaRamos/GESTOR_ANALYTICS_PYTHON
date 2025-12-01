"""
Archivo principal de la aplicación FastAPI.
Define el punto de entrada y un endpoint de prueba /health.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import proyectos
from app.routers import metricas

app = FastAPI()

# Configuración de CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200", 
         "https://gestion-fronted-wrgn.vercel.app", # Frontend Angular
        "http://localhost:8000",  # Backend PHP (si es necesario)
          "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proyectos.router)
app.include_router(metricas.router)

@app.get("/health")
def health_check():
    """Endpoint de prueba para verificar el estado de la API."""
    return {"status": "ok"}
