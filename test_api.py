import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.main import app
from app.models import Record, User

client = TestClient(app)

TEST_PASSWORD = "test123"


@pytest.fixture
def temp_user():
    """创建临时用户，测试结束后删掉。不依赖数据库里已有的数据。"""
    username = f"test_{uuid.uuid4().hex[:8]}"

    client.post("/register", json={"username": username, "password": TEST_PASSWORD})
    res = client.post("/login", json={"username": username, "password": TEST_PASSWORD})
    token = res.json()["token"]

    yield {"username": username, "token": token}

    with SessionLocal() as db:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        if user is not None:
            db.execute(delete(Record).where(Record.user_id == user.id))
            db.delete(user)
            db.commit()


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["message"] == "你好，这是我的第一个 Web 服务"


def test_records_requires_auth():
    """没带 token，必须 401"""
    res = client.get("/records")
    assert res.status_code == 401


def test_records_rejects_bad_token():
    """带了假 token，也必须 401"""
    res = client.get("/records", headers={"Authorization": "Bearer fake-token"})
    assert res.status_code == 401


def test_login_wrong_password(temp_user):
    """密码错误必须 401"""
    res = client.post(
        "/login",
        json={"username": temp_user["username"], "password": "wrong-password"},
    )
    assert res.status_code == 401


def test_login_success(temp_user):
    """正确密码应该拿到 token"""
    res = client.post(
        "/login",
        json={"username": temp_user["username"], "password": TEST_PASSWORD},
    )
    assert res.status_code == 200
    assert "token" in res.json()


def test_full_flow(temp_user):
    headers = {"Authorization": f"Bearer {temp_user['token']}"}

    # ① 新用户一开始没有记录
    res = client.get("/records", headers=headers)
    assert res.json()["items"] == []
    assert res.json()["total"] == 0

    # ② 记一笔
    res = client.post("/records", json={"item": "测试项目", "amount": 12.5}, headers=headers)
    assert res.status_code == 200
    record_id = res.json()["id"]

    # ③ 能查到
    res = client.get("/records", headers=headers)
    body = res.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["item"] == "测试项目"

    # ④ 统计正确
    res = client.get("/summary", headers=headers)
    assert res.json()["count"] == 1
    assert res.json()["total"] == 12.5

    # ⑤ 删除
    res = client.delete(f"/records/{record_id}", headers=headers)
    assert res.status_code == 200

    # ⑥ 删完就没了
    res = client.get("/records", headers=headers)
    assert res.json()["items"] == []
    assert res.json()["total"] == 0
