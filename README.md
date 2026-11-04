# 记账 API · Expense API

> 一个带用户体系的记账后端：注册 / 登录 / JWT 鉴权 / 数据按用户隔离 / 分页 / 完整 CRUD，附带一个可直接使用的网页界面。

**FastAPI** · **MySQL 8** · **PyMySQL** · **bcrypt** · **JWT** · **pytest** · 原生 HTML + JavaScript

---

## 功能

| 模块 | 能力 |
| --- | --- |
| 用户 | 注册（bcrypt 哈希）、登录（签发 JWT） |
| 鉴权 | 所有业务接口需携带 `Authorization: Bearer <token>` |
| 记账 | 新增、查询、修改、删除 |
| 统计 | 笔数与总金额 |
| 分页 | `?page=1&size=10`，返回总数与总页数 |
| 前端 | 登录、记账、删除、翻页，纯 HTML + fetch |

## 技术要点

**1. 密码只存哈希，不存明文**

```python
password_hash = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
```

`gensalt()` 为每个用户生成独立随机盐，同一密码每次哈希结果都不同，防止彩虹表攻击。

**2. JWT 鉴权**

登录成功签发 24 小时有效的 token；接口通过依赖注入统一校验：

```python
def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    try:
        return jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
```

**3. 数据隔离与越权防护**

`records` 表带 `user_id`。**所有读写操作都同时匹配记录 id 与当前用户**：

```python
cursor.execute(
    "DELETE FROM records WHERE id = %s AND user_id = %s",
    (record_id, user["user_id"]),
)
```

少了 `AND user_id = %s`，任何登录用户都能通过猜 id 操作他人的数据（IDOR）。记录不存在与不属于本人统一返回 404，避免暴露 id 是否有效。

**4. 分页**

```python
offset = (page - 1) * size
cursor.execute(
    "SELECT ... WHERE user_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
    (user["user_id"], size, offset),
)
```

同时返回 `total` 与 `pages = (total + size - 1) // size`，前端据此渲染翻页按钮。

**5. 参数校验零代码**

```python
page: int = Query(1, ge=1),
size: int = Query(10, ge=1, le=100),
```

`?page=0` 或 `?size=999` 自动返回 422；请求体由 pydantic 模型校验类型，无需手写判断。

**6. 连接管理**

每个接口使用 `try/finally` 确保连接一定关闭。否则一次异常就会泄漏连接、锁住表，最终拖垮数据库。

## 接口

| 方法 | 路径 | 说明 | 需要登录 |
| --- | --- | --- | --- |
| GET | `/` | 服务信息 | 否 |
| GET | `/ui` | 网页界面 | 否（页面内登录） |
| POST | `/register` | 注册 | 否 |
| POST | `/login` | 登录，返回 token | 否 |
| GET | `/records?page=&size=` | 分页查询自己的记录 | 是 |
| POST | `/records` | 新增一条 | 是 |
| PUT | `/records/{id}` | 修改一条 | 是 |
| DELETE | `/records/{id}` | 删除一条 | 是 |
| GET | `/summary` | 笔数与总额 | 是 |

自动生成的交互式文档：`http://127.0.0.1:8000/docs`

## 快速开始

**环境**：Python 3.11+ · MySQL 8

```bash
# 1. 建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置数据库
copy config.example.py config.py     # 填入数据库账号、密码与库名

# 3. 建表（执行 Alembic 迁移）
alembic upgrade head

# 4. 启动
uvicorn app.main:app --reload
```

打开：

- 网页界面 `http://127.0.0.1:8000/ui`
- 接口文档 `http://127.0.0.1:8000/docs`

首次使用需先调用 `POST /register` 创建一个账号。

## 测试

```bash
pytest
```

`test_api.py` 覆盖：

- 服务可用性与首页响应
- 未带 token / 伪造 token 均返回 401
- 密码错误返回 401，正确返回 token
- 完整业务流程：新用户无数据 → 记账 → 查询 → 统计 → 删除 → 确认清空

测试使用 `pytest.fixture` 创建临时用户，**并在测试结束后自动清理**（利用 `yield` 的后续执行），不会污染真实数据：

```python
@pytest.fixture
def temp_user():
    username = f"test_{uuid.uuid4().hex[:8]}"
    ...注册并登录...
    yield {"username": username, "token": token}
    ...删除该用户的记录与账号...
```

## 项目结构

```text
app/                FastAPI 应用包：路由、鉴权、ORM 模型、数据库访问
index.html          网页界面（登录 / 记账 / 删除 / 分页）
migrations/         Alembic 迁移脚本（表结构的唯一真实来源）
test_api.py         接口测试
config.example.py   配置模板（复制为 config.py 后填写）
requirements.txt    依赖清单
```

## 安全说明

- `config.py` 已被 `.gitignore` 排除，**密钥不入库**
- 密码使用 bcrypt 哈希，数据库中没有明文
- 所有 SQL 使用参数化查询（`%s`），不使用字符串拼接，避免 SQL 注入
- 业务接口全部校验 token，并校验数据归属
- 生产环境请将 `jwt_secret` 替换为至少 32 字节的随机字符串
