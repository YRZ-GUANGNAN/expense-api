from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, Header, Depends, Query
from pydantic import BaseModel
import pymysql
import bcrypt
import jwt
import datetime

from config import (
    db_host,
    db_port,
    db_user,
    db_password,
    db_name,
    jwt_secret,
)

JWT_SECRET = jwt_secret


class UserIn(BaseModel):
    username: str
    password: str


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = authorization[7:]          # 去掉 "Bearer "
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")

    return payload


app = FastAPI()


@app.get("/ui")
def ui():
    return FileResponse("index.html")


def get_conn():
    return pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor,
    )

class RecordIn(BaseModel):
    item: str
    amount: float

@app.get("/")
def root():
    return {"message": "你好，这是我的第一个 Web 服务"}

@app.get("/hello/{name}")
def hello(name: str):
    return {"message": f"你好，{name}"}


# ==================== 以下接口加了保护 ====================

@app.get("/records")
def list_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: dict = Depends(current_user),
):
    offset = (page - 1) * size

    conn = get_conn()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, item, amount, created_at FROM records "
            "WHERE user_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
            (user["user_id"], size, offset),
        )
        items = cursor.fetchall()

        cursor.execute(
            "SELECT COUNT(*) AS c FROM records WHERE user_id = %s",
            (user["user_id"],),
        )
        total = cursor.fetchone()["c"]

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size,
        }
    finally:
        conn.close()


@app.post("/records")
def add_record(record: RecordIn, user: dict = Depends(current_user)):  # <--- 加了依赖
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO records (item, amount, user_id) VALUES (%s, %s, %s)",
            (record.item, record.amount, user["user_id"]),
        )
        conn.commit()
        return {"ok": True, "id": cursor.lastrowid}
    finally:
        conn.close()


@app.get("/summary")
def summary(user: dict = Depends(current_user)):  # <--- 加了依赖
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS count, IFNULL(SUM(amount), 0) AS total "
            "FROM records WHERE user_id = %s",
            (user["user_id"],),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@app.delete("/records/{record_id}")
def delete_record(record_id: int, user: dict = Depends(current_user)):  # <--- 加了依赖
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM records WHERE id = %s AND user_id = %s",
            (record_id, user["user_id"]),
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="该记录不存在")

        return {"ok": True, "message": f"成功删除 id 为 {record_id} 的记录"}
    finally:
        conn.close()

# =========================================================


@app.post("/register")
def register(user: UserIn):
    conn = get_conn()
    try:
        cursor = conn.cursor()

        # ① 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")

        # ② 哈希密码
        password_hash = bcrypt.hashpw(
            user.password.encode(),
            bcrypt.gensalt()
        ).decode()

        # ③ 存入
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (user.username, password_hash),
        )
        conn.commit()
        return {"ok": True, "id": cursor.lastrowid}
    finally:
        conn.close()


@app.post("/login")
def login(user: UserIn):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (user.username,),
        )
        row = cursor.fetchone()

        # ① 用户不存在 或 ② 密码不对 —— 都返回同一句话
        if not row or not bcrypt.checkpw(user.password.encode(), row["password_hash"].encode()):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # ③ 签发 token
        payload = {
            "user_id": row["id"],
            "username": row["username"],
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return {"token": token, "username": row["username"]}
    finally:
        conn.close()
@app.put("/records/{record_id}")
def update_record(record_id: int, record: RecordIn, user: dict = Depends(current_user)):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE records SET item = %s, amount = %s WHERE id = %s AND user_id = %s",
            (record.item, record.amount, record_id, user["user_id"]),
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="该记录不存在或不属于你")

        return {"ok": True, "id": record_id}
    finally:
        conn.close()