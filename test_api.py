import uuid
import pytest
from app import get_conn
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


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


def test_login_wrong_password():
    """密码错误必须 401"""
    res = client.post("/login", json={"username": "xiaoming", "password": "wrong"})
    assert res.status_code == 401


def test_login_success():
    """正确密码应该拿到 token"""
    res = client.post("/login", json={"username": "xiaoming", "password": "123456"})
    assert res.status_code == 200
    assert "token" in res.json()
@pytest.fixture
def temp_user():
    """创建临时用户，测试结束后删掉。"""
    username = f"test_{uuid.uuid4().hex[:8]}"
    password = "test123"

    # 准备：注册 + 登录
    client.post("/register", json={"username": username, "password": password})
    res = client.post("/login", json={"username": username, "password": password})
    token = res.json()["token"]

    yield {"username": username, "token": token}

    # 清理：删掉这个用户的记录和账号
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM records WHERE user_id = (SELECT id FROM users WHERE username = %s)",
            (username,),
        )
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
    finally:
        conn.close()


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

    # ⑤ 修改
    res = client.put(
        f"/records/{record_id}",
        json={"item": "改名了", "amount": 20},
        headers=headers,
    )
    assert res.status_code == 200

    res = client.get("/records", headers=headers)
    assert res.json()["items"][0]["item"] == "改名了"
    assert res.json()["items"][0]["amount"] == 20

    # ⑥ 删除
    res = client.delete(f"/records/{record_id}", headers=headers)
    assert res.status_code == 200

    # ⑦ 删完就没了
    res = client.get("/records", headers=headers)
    assert res.json()["items"] == []
    assert res.json()["total"] == 0


def test_pagination(temp_user):
    headers = {"Authorization": f"Bearer {temp_user['token']}"}

    for i in range(12):
        client.post(
            "/records",
            json={"item": f"item{i}", "amount": 1},
            headers=headers,
        )

    res = client.get("/records?page=1&size=5", headers=headers)
    body = res.json()
    assert body["total"] == 12
    assert body["pages"] == 3
    assert len(body["items"]) == 5

    res = client.get("/records?page=3&size=5", headers=headers)
    assert len(res.json()["items"]) == 2

    # 参数越界由 Query(ge/le) 拦截
    assert client.get("/records?page=0", headers=headers).status_code == 422
    assert client.get("/records?size=999", headers=headers).status_code == 422