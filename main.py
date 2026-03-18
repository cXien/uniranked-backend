"""
Uni Ranked — Backend principal
API REST con FastAPI para manejar cuentas, partidas y rankings.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import inicializar_db
from routers import auth, partidas, jugadores, rankings

app = FastAPI(
    title="Uni Ranked API",
    description="Backend del sistema competitivo de Bedwars para UniversoCraft",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    inicializar_db()

app.include_router(auth.router,      prefix="/auth",      tags=["Autenticacion"])
app.include_router(partidas.router,  prefix="/partidas",  tags=["Partidas"])
app.include_router(jugadores.router, prefix="/jugadores", tags=["Jugadores"])
app.include_router(rankings.router,  prefix="/rankings",  tags=["Rankings"])

@app.get("/")
def raiz():
    return {"status": "ok", "version": "1.0.0"}