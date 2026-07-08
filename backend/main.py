"""
====================================================================
SINAPSIS — Punto de entrada de la API
Ubicación: backend/main.py
====================================================================
API de solo lectura que expone los datos procesados del pipeline SECI
al frontend. Sirve datos REALES: peruanismos clasificados, estadísticas
del embudo, estado del pipeline, y registro de auditoría.

Ejecución:  uvicorn main:app --reload   (desde backend/)
====================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import peruanismos, pipeline, ingeniero, analista, lexicografo

app = FastAPI(
    title="SINAPSIS API",
    description="API del modelo SECI para la riqueza semántica del español peruano en WordNet",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sinapsis-five.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(peruanismos.router)
app.include_router(pipeline.router)
app.include_router(ingeniero.router, prefix="/api/ingeniero", tags=["ingeniero"])
app.include_router(analista.router, prefix="/api/analista", tags=["analista"])
app.include_router(lexicografo.router, prefix="/api/lexicografo", tags=["lexicografo"])


@app.get("/")
def root():
    return {"proyecto": "SINAPSIS", "estado": "operativo", "version": "0.1.0"}