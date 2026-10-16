import psycopg
from app.config import settings


def get_connection(*, connect_timeout: int | None = None, statement_timeout_ms: int | None = None):
    options = None
    if statement_timeout_ms is not None:
        options = f"-c statement_timeout={int(statement_timeout_ms)}"
    kwargs = {}
    if connect_timeout is not None:
        kwargs["connect_timeout"] = int(connect_timeout)
    if options is not None:
        kwargs["options"] = options
    return psycopg.connect(settings.database_url, **kwargs)
