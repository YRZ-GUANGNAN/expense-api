import os

import jwt
from fastapi import Header, HTTPException

try:  # 本地开发用 config.py；容器里没有这个文件，全靠环境变量
    from config import jwt_secret as _jwt_secret
except ImportError:
    _jwt_secret = "dev-secret-please-change-in-production"  # noqa: S105

# 环境变量优先：容器/生产环境用 -e JWT_SECRET=... 覆盖
JWT_SECRET = os.environ.get("JWT_SECRET", _jwt_secret)


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期") from None

    return payload
