"""
Uni Ranked — Base de datos del backend
SQLite para desarrollo, facil de migrar a PostgreSQL en produccion.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "uniranked.db"


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db():
    conn = conectar()
    c    = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS jugadores (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            email             TEXT    UNIQUE NOT NULL,
            password_hash     TEXT    NOT NULL,
            nick              TEXT    UNIQUE NOT NULL,
            nick_verificado   INTEGER DEFAULT 0,
            elo               INTEGER DEFAULT 1000,
            partidas          INTEGER DEFAULT 0,
            victorias         INTEGER DEFAULT 0,
            kills_totales     INTEGER DEFAULT 0,
            muertes_totales   INTEGER DEFAULT 0,
            camas_totales     INTEGER DEFAULT 0,
            fecha_registro    TEXT    NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS partidas (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            jugador_nick       TEXT    NOT NULL,
            modo               TEXT    NOT NULL,
            resultado          TEXT    NOT NULL,
            equipo_ganador     TEXT    DEFAULT '',
            cama_propia        INTEGER DEFAULT 1,
            kills_normales     INTEGER DEFAULT 0,
            kills_finales      INTEGER DEFAULT 0,
            muertes            INTEGER DEFAULT 0,
            muerte_final       INTEGER DEFAULT 0,
            camas_destruidas   INTEGER DEFAULT 0,
            equipos_eliminados INTEGER DEFAULT 0,
            duracion_segundos  INTEGER DEFAULT 0,
            elo_antes          INTEGER DEFAULT 0,
            elo_despues        INTEGER DEFAULT 0,
            elo_cambio         INTEGER DEFAULT 0,
            abandono           INTEGER DEFAULT 0,
            firma              TEXT    DEFAULT '',
            fecha              TEXT    NOT NULL,
            FOREIGN KEY (jugador_nick) REFERENCES jugadores(nick)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS temporadas (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            numero  INTEGER NOT NULL,
            inicio  TEXT    NOT NULL,
            fin     TEXT,
            activa  INTEGER DEFAULT 1
        )
    """)

    c.execute("SELECT COUNT(*) FROM temporadas")
    if c.fetchone()[0] == 0:
        from datetime import datetime
        c.execute(
            "INSERT INTO temporadas (numero, inicio, activa) VALUES (1, ?, 1)",
            (datetime.now().isoformat(),)
        )

    conn.commit()
    conn.close()