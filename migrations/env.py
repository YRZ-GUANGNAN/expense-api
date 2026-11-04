from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 必须导入 app.models：User / Record 只有被 import 时才会执行 __table__ 注册，
# Base.metadata 才会包含这两张表。漏掉这一行，autogenerate 会认为"模型里一张表都没有"，
# 进而生成"DROP TABLE users / records"这种灾难性迁移。
import app.models  # noqa: F401
from app.db import Base, engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 把 app.db 里拼好的 URL（含明文密码）注入 alembic config。
#   - render_as_string(hide_password=False)：str(engine.url) 会把密码渲染成 "***"，
#     engine_from_config 拿到的是 mysql+pymysql://user:***@host/db，连不上。
#   - .replace("%", "%%")：configparser 默认开启 % 插值，
#     密码里出现 % 会抛 InterpolationSyntaxError。
config.set_main_option(
    "sqlalchemy.url",
    engine.url.render_as_string(hide_password=False).replace("%", "%%"),
)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
