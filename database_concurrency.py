import sqlite3
import threading
from contextlib import contextmanager
from functools import wraps

_WRITE_LOCK = threading.RLock()


@contextmanager
def database_write_lock():
    with _WRITE_LOCK:
        yield


def serialized_database_write(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with database_write_lock():
            return function(*args, **kwargs)

    return wrapped


def connect_database(db_path, isolation_level=""):
    with database_write_lock():
        connection = sqlite3.connect(
            db_path,
            timeout=20,
            check_same_thread=True,
            isolation_level=isolation_level,
        )
        try:
            journal_mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()
            if not journal_mode or journal_mode[0].lower() != "wal":
                raise RuntimeError(f"Could not enable SQLite WAL mode for {db_path}")
            connection.execute("PRAGMA busy_timeout=20000")
        except Exception:
            connection.close()
            raise
        return connection
