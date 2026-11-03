import datetime
import logging

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException

from app.auth import JWT_SECRET
from app.db import db_conn
from app.schemas import UserIn

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register")
def register(user: UserIn):
    with db_conn() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            logger.warning("注册失败（用户名已存在）: %s", user.username)
            raise HTTPException(status_code=400, detail="用户名已存在")

        password_hash = bcrypt.hashpw(
            user.password.encode(),
            bcrypt.gensalt(),
        ).decode()

        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (user.username, password_hash),
        )
        conn.commit()
        new_id = cursor.lastrowid

    logger.info("注册成功: %s (id=%s)", user.username, new_id)
    return {"ok": True, "id": new_id}


@router.post("/login")
def login(user: UserIn):
    with db_conn() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (user.username,),
        )
        row = cursor.fetchone()

    if not row or not bcrypt.checkpw(user.password.encode(), row["password_hash"].encode()):
        logger.warning("登录失败: %s", user.username)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    payload = {
        "user_id": row["id"],
        "username": row["username"],
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    logger.info("登录成功: %s", user.username)
    return {"token": token, "username": row["username"]}
