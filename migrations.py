"""Schema migration runner for the Neuro Core 2 SQLite store.

PRAGMA user_version ownership
-----------------------------
PRAGMA user_version is owned exclusively by this migration runner. No other
code path may read, set, or interpret user_version as a schema marker. The
runner is the only component that may modify user_version, and it does so
only inside a committed migration transaction. Any other code that needs to
know the schema version must call SQLiteStore.schema_version() (an internal
API) or run_migrations(); it must never write user_version directly.
"""
import sqlite3

# The highest schema version this code knows how to migrate to. Databases
# with a user_version greater than this are rejected on open to prevent
# accidental downgrade corruption.
LATEST_SCHEMA_VERSION = 1


def _migration_1(connection: sqlite3.Connection) -> None:
    """Baseline schema (version 1).

    Uses CREATE TABLE IF NOT EXISTS so the migration is additive and
    data-preserving for legacy databases that already contain the tables.
    """
    connection.execute(
        "CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, text TEXT, source TEXT, project TEXT, agent TEXT, importance REAL, confidence REAL, validation TEXT)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS activity_events (event_id TEXT PRIMARY KEY, kind TEXT, project TEXT, agent TEXT, targets TEXT, outcome TEXT, source TEXT, occurred_at TEXT)"
    )


_MIGRATIONS: dict[int, object] = {
    1: _migration_1,
}


def run_migrations(connection: sqlite3.Connection) -> None:
    """Apply pending schema migrations in ascending order.

    Reads PRAGMA user_version, applies each registered migration whose
    version is greater than the current version, and bumps user_version
    only after each migration commits. Each migration runs inside a
    BEGIN IMMEDIATE transaction; on failure the transaction rolls back
    and the error propagates, leaving user_version unchanged. Running
    the runner again is a no-op because user_version already equals the
    latest known version. On a fresh database (user_version = 0, no
    tables) and on a legacy database (user_version = 0, tables already
    present), the baseline migration converges both to version 1 while
    preserving all existing rows.

    If user_version is greater than the highest migration known to this
    code, a clear error is raised and the database is refused, preventing
    accidental downgrade corruption.
    """
    if connection.in_transaction:
        raise RuntimeError("run_migrations must be called outside an active transaction")

    current = connection.execute("PRAGMA user_version").fetchone()[0]
    if current > LATEST_SCHEMA_VERSION:
        raise RuntimeError(
            f"database schema version {current} is newer than this code supports "
            f"(latest known version {LATEST_SCHEMA_VERSION}); refusing to open to "
            "prevent accidental downgrade corruption"
        )

    for version in range(current + 1, LATEST_SCHEMA_VERSION + 1):
        connection.execute("BEGIN IMMEDIATE")
        try:
            _MIGRATIONS[version](connection)
            connection.execute(f"PRAGMA user_version = {version}")
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
