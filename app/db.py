import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

try:  # 本地开发用 config.py；容器里没有这个文件，全靠环境变量
    from config import db_host, db_name, db_password, db_port, db_user
except ImportError:
    db_host, db_port, db_user, db_password, db_name = "localhost", 3306, "", "", ""

# 环境变量优先，config.py 兜底。
# 容器里不能用 localhost：那指向容器自己，而不是宿主机上的 MySQL。
_db_host = os.environ.get("DB_HOST", db_host)
_db_port = os.environ.get("DB_PORT", db_port)
_db_user = os.environ.get("DB_USER", db_user)
_db_password = os.environ.get("DB_PASSWORD", db_password)
_db_name = os.environ.get("DB_NAME", db_name)

DB_URL = (
    f"mysql+pymysql://{quote_plus(_db_user)}:{quote_plus(_db_password)}"
    f"@{_db_host}:{_db_port}/{_db_name}"
)
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
