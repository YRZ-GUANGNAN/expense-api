import os
from contextlib import contextmanager

import pymysql

try:  # 本地开发用 config.py；容器里没有这个文件，全靠环境变量
    from config import db_host, db_name, db_password, db_port, db_user
except ImportError:
    db_host, db_port, db_user, db_password, db_name = "localhost", 3306, "", "", ""

# 环境变量优先，config.py 兜底。
# 容器里不能用 localhost：那指向容器自己，而不是宿主机上的 MySQL。
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", db_host),
    "port": int(os.environ.get("DB_PORT", db_port)),
    "user": os.environ.get("DB_USER", db_user),
    "password": os.environ.get("DB_PASSWORD", db_password),
    "database": os.environ.get("DB_NAME", db_name),
}


def get_conn():
    return pymysql.connect(
        **DB_CONFIG,
        cursorclass=pymysql.cursors.DictCursor,
    )


@contextmanager
def db_conn():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
