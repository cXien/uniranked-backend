"""
Uni Ranked — Utilidades de autenticacion
JWT para tokens de sesion, bcrypt para contraseñas.
"""

import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY  = os.getenv("SECRET_KEY", "uniranked-dev-secret-cambiar-en-produccion")
ALGORITHM   = "HS256"
TOKEN_HORAS = 720  # 30 dias

pwd_context    = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme  = OAuth2PasswordBearer(tokenUrl="/auth/login")


import hashlib

def hashear_password(password: str) -> str:
    # bcrypt tiene limite de 72 bytes — pre-hasheamos con sha256 para evitar el limite
    pre = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(pre)


def verificar_password(password: str, hashed: str) -> bool:
    pre = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.verify(pre, hashed)


def crear_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_HORAS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado"
        )


def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decodificar_token(token)
    email   = payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Token invalido")
    return payload