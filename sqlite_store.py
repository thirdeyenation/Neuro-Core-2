"""SQLite implementation of the Neuro Core memory-store port."""
import sqlite3
from datetime import datetime
from memory_lifecycle import ValidationState
from neuro_core_2 import Memory, Scope
from activity_ledger import ActivityEvent
from migrations import run_migrations

# Default busy timeout in milliseconds. This is the bounded wait a writer
# tolerates when another writer holds the SQLite write lock. It is
# configurable via the busy_timeout_ms constructor argument; the default
# is 5000 ms (5 seconds).
DEFAULT_BUSY_TIMEOUT_MS = 5000


class SQLiteStore:
    def __init__(self, path: str = "neuro_core_2.db", busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS) -> None:
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
        try:
            run_migrations(self.connection)
        except Exception:
            self.connection.close()
            raise

    def put(self, memory: Memory) -> Memory:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute("INSERT OR REPLACE INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (memory.memory_id, memory.text, memory.source, memory.scope.project, memory.scope.agent, memory.importance, memory.confidence, memory.validation.value))
            self.connection.commit()
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise
        return memory

    def get(self, memory_id: str) -> Memory | None:
        row = self.connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._memory(row) if row else None

    def list(self, scope: Scope) -> tuple[Memory, ...]:
        if scope.agent is None:
            rows = self.connection.execute("SELECT * FROM memories WHERE project = ? AND agent IS NULL", (scope.project,)).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM memories WHERE project = ? AND agent = ?", (scope.project, scope.agent)).fetchall()
        return tuple(self._memory(row) for row in rows)

    def append_event(self, event) -> None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute(
                "INSERT OR REPLACE INTO activity_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (event.event_id, event.kind, event.scope.project, event.scope.agent, ",".join(event.targets), event.outcome, event.evidence.get("source", ""), event.occurred_at.isoformat()),
            )
            self.connection.commit()
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise

    def list_events(self, scope: Scope | None = None) -> tuple[ActivityEvent, ...]:
        if scope is None:
            rows = self.connection.execute("SELECT event_id, kind, project, agent, targets, outcome, source, occurred_at FROM activity_events ORDER BY occurred_at ASC").fetchall()
        else:
            if scope.agent is None:
                rows = self.connection.execute("SELECT event_id, kind, project, agent, targets, outcome, source, occurred_at FROM activity_events WHERE project = ? AND agent IS NULL ORDER BY occurred_at ASC", (scope.project,)).fetchall()
            else:
                rows = self.connection.execute("SELECT event_id, kind, project, agent, targets, outcome, source, occurred_at FROM activity_events WHERE project = ? AND agent = ? ORDER BY occurred_at ASC", (scope.project, scope.agent)).fetchall()
        return tuple(self._event(row) for row in rows)

    def schema_version(self) -> int:
        """Return the current schema version (PRAGMA user_version).

        Internal API only. This method is not part of the MemoryStore port
        and is not exposed through any tool. PRAGMA user_version is owned
        by the migration runner; this method only reads it.
        """
        return self.connection.execute("PRAGMA user_version").fetchone()[0]

    @staticmethod
    def _event(row: tuple) -> ActivityEvent:
        return ActivityEvent(
            kind=row[1],
            scope=Scope(row[2], row[3]),
            targets=tuple(row[4].split(",")) if row[4] else (),
            outcome=row[5],
            evidence={"source": row[6]} if row[6] else {},
            event_id=row[0],
            occurred_at=datetime.fromisoformat(row[7]),
        )

    @staticmethod
    def _memory(row: tuple) -> Memory:
        return Memory(row[1], row[2], Scope(row[3], row[4]), row[5], row[6], ValidationState(row[7]), row[0])

    def close(self) -> None:
        self.connection.close()
