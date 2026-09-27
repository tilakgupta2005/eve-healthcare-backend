"""
Cross-dialect GUID column type.

Stores a native UUID on PostgreSQL, and a 32-char hex string on any other
backend (e.g. SQLite, used for local/dev/test runs). This lets the exact
same models work against both databases without an `if postgres` branch
scattered through the codebase.

(Standard recipe from the SQLAlchemy docs, adapted for SQLAlchemy 2.x.)
"""
import uuid

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return f"{value.int:032x}"

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value
