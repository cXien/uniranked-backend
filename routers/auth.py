"""
Uni Ranked — Router de autenticacion
Registro, login y verificacion de nick.
"""

import secrets
import string
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import conectar
from auth_utils import hashear_password, verificar_password, crear_token

router = APIRouter()


class RegistroRequest(BaseModel):
    email:    str
    password: str
    nick:     str


class LoginRequest(BaseModel):
    email:    str
    password: str


class VerificarNickRequest(BaseModel):
    email:  str
    codigo: str


def generar_codigo() -> str:
    chars  = string.ascii_uppercase + string.digits
    codigo = "".join(secrets.choice(chars) for _ in range(6))
    return f"UC-{codigo}"


def asegurar_tabla_codigos(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS codigos_verificacion (
            email  TEXT PRIMARY KEY,
            codigo TEXT NOT NULL,
            fecha  TEXT NOT NULL
        )
    """)
    conn.commit()


@router.post("/registro")
def registro(req: RegistroRequest):
    email = req.email.strip().lower()
    nick  = req.nick.strip()

    if not email or "@" not in email:
        raise HTTPException(400, "Email invalido")
    if len(req.password) < 6:
        raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")
    if not nick:
        raise HTTPException(400, "El nick no puede estar vacio")

    conn = conectar()
    try:
        asegurar_tabla_codigos(conn)

        if conn.execute("SELECT 1 FROM jugadores WHERE email = ?", (email,)).fetchone():
            raise HTTPException(400, "Ya existe una cuenta con ese email")

        if conn.execute(
            "SELECT 1 FROM jugadores WHERE LOWER(nick) = LOWER(?)", (nick,)
        ).fetchone():
            raise HTTPException(400, f"El nick '{nick}' ya esta en uso")

        password_hash = hashear_password(req.password)
        codigo        = generar_codigo()

        conn.execute("""
            INSERT INTO jugadores (email, password_hash, nick, fecha_registro)
            VALUES (?, ?, ?, ?)
        """, (email, password_hash, nick, datetime.now().isoformat()))

        conn.execute("""
            INSERT OR REPLACE INTO codigos_verificacion (email, codigo, fecha)
            VALUES (?, ?, ?)
        """, (email, codigo, datetime.now().isoformat()))

        conn.commit()

        return {
            "ok":                  True,
            "codigo_verificacion": codigo,
            "mensaje":             f"Cuenta creada. Escribe {codigo} en el chat de UniversoCraft."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error interno: {str(e)}")
    finally:
        conn.close()


@router.post("/login")
def login(req: LoginRequest):
    email = req.email.strip().lower()
    conn  = conectar()
    try:
        asegurar_tabla_codigos(conn)

        jugador = conn.execute(
            "SELECT * FROM jugadores WHERE email = ?", (email,)
        ).fetchone()

        if not jugador or not verificar_password(req.password, jugador["password_hash"]):
            raise HTTPException(401, "Email o contraseña incorrectos")

        codigo = None
        if not jugador["nick_verificado"]:
            row = conn.execute(
                "SELECT codigo FROM codigos_verificacion WHERE email = ?", (email,)
            ).fetchone()
            if row:
                codigo = row["codigo"]

        token = crear_token({"email": email, "nick": jugador["nick"]})

        return {
            "ok":                  True,
            "token":               token,
            "nick":                jugador["nick"],
            "nick_verificado":     bool(jugador["nick_verificado"]),
            "elo":                 jugador["elo"],
            "codigo_verificacion": codigo
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error interno: {str(e)}")
    finally:
        conn.close()


@router.post("/verificar-nick")
def verificar_nick(req: VerificarNickRequest):
    email  = req.email.strip().lower()
    codigo = req.codigo.strip().upper()
    conn   = conectar()
    try:
        asegurar_tabla_codigos(conn)

        row = conn.execute(
            "SELECT codigo FROM codigos_verificacion WHERE email = ?", (email,)
        ).fetchone()

        if not row:
            raise HTTPException(400, "No hay verificacion pendiente para este email")

        if row["codigo"] != codigo:
            raise HTTPException(400, "Codigo incorrecto")

        conn.execute(
            "UPDATE jugadores SET nick_verificado = 1 WHERE email = ?", (email,)
        )
        conn.execute(
            "DELETE FROM codigos_verificacion WHERE email = ?", (email,)
        )
        conn.commit()
        return {"ok": True, "mensaje": "Nick verificado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error interno: {str(e)}")
    finally:
        conn.close()