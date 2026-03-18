"""
Uni Ranked — Router de rankings
Leaderboard global y por modo.
"""

from fastapi import APIRouter
from database import conectar

router = APIRouter()


@router.get("/")
def leaderboard(limite: int = 50):
    conn = conectar()
    try:
        rows = conn.execute("""
            SELECT nick, elo, partidas, victorias, kills_totales, camas_totales
            FROM jugadores
            WHERE nick_verificado = 1
              AND partidas >= 10
            ORDER BY elo DESC
            LIMIT ?
        """, (min(limite, 100),)).fetchall()

        resultado = []
        for i, r in enumerate(rows):
            j        = dict(r)
            winrate  = round((j["victorias"] / max(j["partidas"], 1)) * 100, 1)
            resultado.append({
                "posicion": i + 1,
                "nick":     j["nick"],
                "elo":      j["elo"],
                "partidas": j["partidas"],
                "winrate":  winrate,
                "kills":    j["kills_totales"],
                "camas":    j["camas_totales"],
            })
        return resultado
    finally:
        conn.close()


@router.get("/posicion/{nick}")
def posicion(nick: str):
    conn = conectar()
    try:
        jugador = conn.execute(
            "SELECT elo FROM jugadores WHERE LOWER(nick) = LOWER(?) AND nick_verificado = 1",
            (nick,)
        ).fetchone()

        if not jugador:
            return {"posicion": None}

        pos = conn.execute("""
            SELECT COUNT(*) FROM jugadores
            WHERE elo > ? AND nick_verificado = 1 AND partidas >= 10
        """, (jugador["elo"],)).fetchone()[0]

        return {"posicion": pos + 1, "elo": jugador["elo"]}
    finally:
        conn.close()