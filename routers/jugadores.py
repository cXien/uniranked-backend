"""
Uni Ranked — Router de jugadores
Perfil publico, stats y busqueda.
"""

from fastapi import APIRouter, HTTPException
from database import conectar

router = APIRouter()


@router.get("/{nick}")
def perfil(nick: str):
    conn = conectar()
    try:
        jugador = conn.execute(
            "SELECT * FROM jugadores WHERE LOWER(nick) = LOWER(?)", (nick,)
        ).fetchone()

        if not jugador:
            raise HTTPException(404, f"Jugador '{nick}' no encontrado")

        j        = dict(jugador)
        partidas = j["partidas"]
        kills    = j["kills_totales"]
        muertes  = j["muertes_totales"]
        victorias = j["victorias"]

        kda     = round(kills / max(muertes, 1), 2)
        winrate = round((victorias / max(partidas, 1)) * 100, 1)

        return {
            "nick":      j["nick"],
            "elo":       j["elo"],
            "partidas":  partidas,
            "victorias": victorias,
            "winrate":   winrate,
            "kda":       kda,
            "kills":     kills,
            "muertes":   muertes,
            "camas":     j["camas_totales"],
        }
    finally:
        conn.close()


@router.get("/buscar/{query}")
def buscar(query: str):
    conn = conectar()
    try:
        rows = conn.execute("""
            SELECT nick, elo, partidas, victorias
            FROM jugadores
            WHERE LOWER(nick) LIKE LOWER(?)
              AND nick_verificado = 1
            ORDER BY elo DESC
            LIMIT 10
        """, (f"%{query}%",)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()