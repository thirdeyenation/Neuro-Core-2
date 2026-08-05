# Schema Test Sketch — Required Before Table Evolution

## Goal

Protect the verified SQLite-backed runtime before any table shape changes are introduced.

## Next test to add

Create a unit/integration test that proves the SQLite schema remains compatible across restart and additive event writes. The minimal test should:

1. Create a temporary SQLite database with the current schema.
2. Insert one memory and one activity event.
3. Close and reopen the database.
4. Assert that the original memory is still retrievable.
5. Assert that the activity event is still readable through `list_activity(...)`.
6. Assert that a second memory/event can be appended without rewriting or deleting the original rows.
7. Assert that the schema version (if added later) is either unchanged or explicitly migrated by a versioned path.

## Acceptance rule

No table-shape change is release-ready until this test passes against the updated schema and a migration note is recorded in `docs/decisions/`.
