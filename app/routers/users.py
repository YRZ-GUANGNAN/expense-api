import datetime
import logging

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import JWT_SECRET
from app.db import get_db
from app.models import User
from app.schemas import UserIn

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register")
def register(user: UserIn, db: Session = Depends(get_db)):
    existing = db.execute(
        select(User).where(User.username == user.username)
    ).scalar_one_or_none()
    if existing:
        logger.warning("注册失败（用户名已存在）: %s", user.username)
        raise HTTPException(status_code=400, detail="用户名已存在")

    password_hash = bcrypt.hashpw(
        user.password.encode(),
        bcrypt.gensalt(),
    ).decode()

    new_user = User(username=user.username, password_hash=password_hash)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("注册成功: %s (id=%s)", user.username, new_user.id)
    return {"ok": True, "id": new_user.id}


@router.post("/login")
def login(user: UserIn, db: Session = Depends(get_db)):
    db_user = db.execute(
        select(User).where(User.username == user.username)
    ).scalar_one_or_none()

    if not db_user or not bcrypt.checkpw(
        user.password.encode(), db_user.password_hash.encode()
    ):
        logger.warning("登录失败: %s", user.username)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    payload = {
        "user_id": db_user.id,
        "username": db_user.username,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    logger.info("登录成功: %s", user.username)
    return {"token": token, "username": db_user.username}
