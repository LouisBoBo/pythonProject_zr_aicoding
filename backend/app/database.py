from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# SQLite + QueuePool 易把未结束事务留在池里，造成进程内读到陈旧快照、
# 与其它连接已提交数据互相看不到（工单列表只剩几条即典型症状）。
# 文件库一律 NullPool，每次请求短连接；WAL + busy_timeout 降低锁冲突。
_is_sqlite = str(settings.database_url).startswith("sqlite")
_engine_kwargs: dict = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    _engine_kwargs["poolclass"] = NullPool
engine = create_engine(settings.database_url, **_engine_kwargs)
if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_on_connect(dbapi_conn, _connection_record) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
