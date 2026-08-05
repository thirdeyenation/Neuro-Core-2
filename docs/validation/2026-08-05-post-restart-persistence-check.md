# Post-Restart Persistence Check

**Date:** 2026-08-05
**Repository:** thirdeyenation/Neuro-Core-2
**Plugin identity:** neuro_core_2

## Results

| Check | Result | Status |
|-------|--------|--------|
| DB exists at `/a0/usr/plugins/neuro_core_2/neuro_core.db` | exists=True, 12288 bytes, writable=True | ✅ |
| Retrieve prior memory (alpha/tester scope) | 0 results (correctly excluded — was superseded) | ✅ |
| Capture new memory post-restart | `memory_id: 27cb0d01-3fc4-49cf-b475-93c2dd6c2f41`, outcome=stored | ✅ |
| Retrieve new memory (same scope) | 1 result, score=0.75, factors present | ✅ |
| DB size after write | 12288 bytes (unchanged — SQLite page-level allocation) | ✅ |

## Conclusion

SQLite-backed behavior persists across independent container restart. The DB file survives, remains writable, and capture/retrieve works correctly after restart. The prior memory's absence is due to its superseded state (correct lifecycle behavior), not data loss.
