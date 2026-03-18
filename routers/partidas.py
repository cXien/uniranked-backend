"""
Uni Ranked — Router de partidas
Subir partidas, historial y validacion.
"""

from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import conectar
from auth_utils import obtener_usuario_actual

router = APIRouter()

# -------------------------------------------------------
# Configuracion de ELO (igual que en el cliente)
# -------------------------------------------------------
PUNTOS_VICTORIA       = 18
PUNTOS_DERROTA        = -16
PENALIZACION_ABANDONO = -12
PARTIDAS_CALIBRACION  = 10
BONUS_CAMA_EN_PIE     = 4
BONUS_POR_KILL        = 1
BONUS_POR_KILL_FINAL  = 3
BONUS_POR_CAMA        = 5
PENALIZACION_MUERTE   = -1


class PartidaRequest(BaseModel):
    modo:               str
    resultado:          str
    equipo_ganador:     str = ""
    cama_propia:        bool = True
    kills_normales:     int = 0
    kills_finales:      int = 0
    muertes:            int = 0
    muerte_final:       bool = False
    camas_destruidas:   int = 0
    equipos_eliminados: int = 0
    duracion_segundos:  int = 0
    abandono:           bool = False
    fecha:              str = ""


def calcular_elo(jugador: dict, partida: PartidaRequest) -> dict:
    """Calcula el cambio de ELO en el servidor — misma logica que el cliente."""
    elo_actual = jugador["elo"]
    partidas   = jugador["partidas"]

    if partida.abandono:
        # Contar abandonos del dia
        conn = conectar()
        hoy  = date.today().isoformat()
        abandonos_hoy = conn.execute("""
            SELECT COUNT(*) FROM partidas
            WHERE jugador_nick = ? AND abandono = 1 AND fecha LIKE ?
        """, (jugador["nick"], f"{hoy}%")).fetchone()[0]
        conn.close()

        if abandonos_hoy == 0:
            return {"cambio": 0, "elo_nuevo": elo_actual, "calibracion": False, "abandono": True}
        return {"cambio": PENALIZACION_ABANDONO,
                "elo_nuevo": max(0, elo_actual + PENALIZACION_ABANDONO),
                "calibracion": False, "abandono": True}

    if partidas < PARTIDAS_CALIBRACION:
        return {"cambio": 0, "elo_nuevo": elo_actual, "calibracion": True, "abandono": False}

    victoria = partida.resultado == "victoria"
    base     = PUNTOS_VICTORIA if victoria else PUNTOS_DERROTA
    bonus    = 0

    if partida.cama_propia and not partida.muerte_final:
        bonus += BONUS_CAMA_EN_PIE

    kills = partida.kills_normales + partida.kills_finales
    bonus += partida.kills_normales  * BONUS_POR_KILL
    bonus += partida.kills_finales   * BONUS_POR_KILL_FINAL
    bonus += partida.camas_destruidas * BONUS_POR_CAMA
    bonus += partida.muertes         * PENALIZACION_MUERTE

    cambio    = base + bonus
    elo_nuevo = max(0, elo_actual + cambio)

    return {"cambio": cambio, "elo_nuevo": elo_nuevo, "calibracion": False, "abandono": False}


@router.post("/subir")
def subir_partida(
    req:     PartidaRequest,
    usuario: dict = Depends(obtener_usuario_actual)
):
    email = usuario["email"]
    conn  = conectar()
    try:
        jugador = conn.execute(
            "SELECT * FROM jugadores WHERE email = ?", (email,)
        ).fetchone()

        if not jugador:
            raise HTTPException(404, "Jugador no encontrado")

        if not jugador["nick_verificado"]:
            raise HTTPException(403, "Debes verificar tu nick antes de subir partidas")

        elo_antes     = jugador["elo"]
        resultado_elo = calcular_elo(dict(jugador), req)
        elo_despues   = resultado_elo["elo_nuevo"]
        elo_cambio    = resultado_elo["cambio"]

        fecha = req.fecha or datetime.now().isoformat()

        conn.execute("""
            INSERT INTO partidas (
                jugador_nick, modo, resultado, equipo_ganador,
                cama_propia, kills_normales, kills_finales, muertes,
                muerte_final, camas_destruidas, equipos_eliminados,
                duracion_segundos, elo_antes, elo_despues, elo_cambio,
                abandono, fecha
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            jugador["nick"], req.modo, req.resultado, req.equipo_ganador,
            1 if req.cama_propia else 0,
            req.kills_normales, req.kills_finales, req.muertes,
            1 if req.muerte_final else 0,
            req.camas_destruidas, req.equipos_eliminados,
            req.duracion_segundos, elo_antes, elo_despues, elo_cambio,
            1 if req.abandono else 0, fecha
        ))

        # Actualizar stats del jugador
        conn.execute("""
            UPDATE jugadores SET
                elo             = ?,
                partidas        = partidas + 1,
                victorias       = victorias + ?,
                kills_totales   = kills_totales + ?,
                muertes_totales = muertes_totales + ?,
                camas_totales   = camas_totales + ?
            WHERE email = ?
        """, (
            elo_despues,
            1 if req.resultado == "victoria" else 0,
            req.kills_normales + req.kills_finales,
            req.muertes,
            req.camas_destruidas,
            email
        ))

        conn.commit()

        return {
            "ok":          True,
            "elo_antes":   elo_antes,
            "elo_despues": elo_despues,
            "elo_cambio":  elo_cambio,
            "calibracion": resultado_elo["calibracion"],
            "abandono":    resultado_elo["abandono"],
        }
    finally:
        conn.close()


@router.get("/historial/{nick}")
def historial(nick: str, limite: int = 20):
    conn = conectar()
    try:
        rows = conn.execute("""
            SELECT * FROM partidas
            WHERE jugador_nick = ?
            ORDER BY fecha DESC
            LIMIT ?
        """, (nick, min(limite, 50))).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()