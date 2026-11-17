# D1: expensive reads, write amplification and correctness

## 1. Polling that performs a large lookup

Trace the whole route, including identity expansion, trial/entitlement joins, message lookup and logging. A poll that returns no messages can still scan millions of rows. Estimate calls per active client per hour and multiply by measured rows per call.

Inspect joins, correlated subqueries, OR predicates, expressions on indexed columns, sort/group operations, pagination and fan-out. Compare representative query plans with realistic cardinality and skew, not only an empty test database. Verify missing/legacy identity rows remain represented after rewrites. A change from LEFT JOIN to INNER JOIN can silently remove users.

Index existence alone is not proof of efficient access. Statistics and join order matter. Prefer measured indexed lookups; use explicit join-order constraints only with evidence and regression coverage. `PRAGMA optimize` or statistics maintenance is a mutation, not a read-only diagnostic. Command success is not proof that statistics or billed reads changed.

## 2. Read amplification in administration and cron jobs

Look for full-history grouping on each dashboard request, expensive COUNTs, large OFFSET pagination and repeated summaries. Consider derived summaries only if their update, deletion, merge, backfill and repair semantics are defined. Cache or summarize the user's actual query, not a guessed substitute.

Retention should make bounded progress and resume after interruption. Validate indexes on cutoff and ordering columns. Unbounded nightly work can block uploads. A cursor/checkpoint write on every empty scan can itself dominate maintenance costs. Suppress only exactly unchanged progress; preserve crash recovery and eventual cleanup.

## 3. Index write amplification

Inspect actual deployed schema as well as migration files. Legacy/manual indexes can survive even when absent from current bootstrap SQL. D1 index maintenance can add billed writes; benchmark insert/update/delete shapes with the real indexes, including partial-index predicates.

An index on `(owner)` may overlap an index on `(owner, created_at, kind)`. It is a candidate, not automatic proof:

- Compare collations, directions, expressions, partial predicates and uniqueness.
- Never drop a UNIQUE constraint/index merely because a longer nonunique index has the same prefix.
- Check explicit `INDEXED BY`, primary-key/foreign-key enforcement, ordered pagination and exports.
- Equal timestamps may have different tie order when an index changes. Require explicit deterministic ordering when a cursor or user-visible contract depends on it.
- A narrower index can still have a smaller working set; compare representative read cost as well as saved writes.

The offline index helper excludes partial, expression, unique and constraint-owned removal candidates, and requires matching prefix directions/collations with a nonpartial covering index. It still cannot establish workload equivalence or recommend execution.

`CREATE INDEX IF NOT EXISTS` checks a name, not whether the existing definition matches your intended columns. Verify the surviving index definition in deployment preflight/readback. Avoid rebuilding a valid large index just to make an idempotent migration look reassuring. Measure migration cost separately.

## 4. Identical metadata and summaries

Use null-safe exact comparisons when suppressing an UPSERT:

```sql
INSERT INTO summary(owner, first_seen, last_seen, last_logout_seen)
SELECT owner, MIN(created_at), MAX(created_at),
       MAX(CASE WHEN kind = 'logout' THEN created_at END)
FROM events
WHERE true
GROUP BY owner
ON CONFLICT(owner) DO UPDATE SET
  first_seen = excluded.first_seen,
  last_seen = excluded.last_seen,
  last_logout_seen = excluded.last_logout_seen
WHERE summary.first_seen IS NOT excluded.first_seen
   OR summary.last_seen IS NOT excluded.last_seen
   OR summary.last_logout_seen IS NOT excluded.last_logout_seen;
```

The explicit WHERE resolves the documented `INSERT SELECT`/UPSERT parsing ambiguity. Adapt schemas and nullability; this example assumes non-null owner keys and meaningful event timestamps. Nullable keys can create different uniqueness and orphan semantics.

A full rebuild often deletes all summary rows then reinserts them. Replace it with exact delta UPSERT plus orphan deletion in one D1 batch transaction when equivalent. Test new rows, changed first/last times, logout becoming null, deleted owners, identity merges, missing tables and rollback. Inspect triggers: skipping a row update can skip a meaningful side effect even when field values match.

Distinguish `updated_at` as business history from bookkeeping. Updating it only hourly changes information. Do not call that strict-lossless unless the product explicitly permits that precision. Use `COALESCE` only when the original contract intentionally keeps the old value; a full corrective rebuild must be able to clear obsolete fields.

## 5. Rate counters and AUTOINCREMENT

An INSERT/UPSERT against an existing key can incur automatic-ID bookkeeping and maintain a window index even when the window is unchanged. A local D1 experiment may show a hot counter costing three writes versus one for a count-only UPDATE. Treat that as schema/runtime-dependent, not a universal tariff.

Potential shape:

```sql
UPDATE rate_limits SET count = count + 1
WHERE key = ? AND window_start >= ?
RETURNING count;
```

If this succeeds with no row, the original atomic UPSERT can create/reset the window and handle concurrent creation. Preserve the original strict expiry boundary, time source, key derivation, maximum and reject behavior. A new/expired key incurs an extra query; a system dominated by one-off keys may get worse.

Critical asynchronous rule: a timeout race does not cancel database work. A delayed no-match response must not start fallback after the caller has timed out. Use one overall budget, an active/deadline guard immediately before fallback, and no fallback on errors or ambiguous results. Already-started writes may still complete; never replay them or turn a rejected request into success. Check response timing at each stage; do not reset a fresh full timeout for the second query.

Test late no-match, late match, late error, stalled fallback, delayed timer callback, concurrent missing keys, window reset races, cleanup between statements, rejected limits and malformed results. Under load, report timeouts instead of extending limits merely to pass the test. Local bridge performance is not production performance.

Do not remove AUTOINCREMENT globally: retained high-watermark IDs may require non-reuse. Internal ID gaps can change even when logical counters match; inspect all consumers. Native per-location rate-limit bindings are not automatically equivalent to a global D1 policy.

## 6. Ingest, retries and delivery

Distinguish HTTP batches, database batch transactions and retained records. Fewer HTTP uploads can reduce request/ledger/metadata overhead without reducing per-record writes. `db.batch()` reduces round trips; it does not make all row/index writes count as one.

Keep the retry ledger if it protects batch-wide side effects after ambiguous commits. Per-record uniqueness is not necessarily equivalent. Test duplicate upload before/after commit, failure mid-batch, out-of-order retries, lost responses and partial downstream delivery.

Before delaying uploads, inspect in-memory caps, durable journal size, eviction, crash checkpoints, exit flushing and overload behavior. A bounded queue that previously survived can begin dropping records under a longer interval. Do not promise no data loss from batching until durability and overflow tests support it.

## 7. Evidence to retain

For join-index additions, first reproduce the deployed plan, then compare the exact application query on populated fixtures. Cover selective and nonselective date ranges, no recent matches, cutoff equality, null keys, orphan rows and duplicate join keys permitted by the schema. A nonunique index must not silently become a uniqueness constraint. Verify subsequent inserts, key updates and deletes as well as initial results. Record an empty-database plan only as planner feasibility, not as a savings benchmark.

For a cached public counter, distinguish request frequency, per-data-center cache misses and globally coordinated recomputation. Inspect snapshot lease expiry, stale responses and cache freshness together. A shared snapshot can cap scans without making every refresh constant-cost; rolling-window counts still need correct expiry handling. Keep the existing freshness contract unless a change is explicitly accepted.

A post-deployment probe that reads two rows may simply have no recent matches. Compare matching parameters and data distributions, or clearly label the contrast with historical averages as directional rather than a controlled before/after experiment. Verify ordinary traffic over representative windows before projecting savings.

Use synthetic fixtures with actual schema, skew and query shapes. Compare record hashes or canonical sorted records, returned results and query plans before/after. Then measure D1 `rows_read`/`rows_written` metadata in the local Worker runtime. Node SQLite `total_changes()` verifies row-change suppression but is not a substitute for D1's billing counters. Finally verify the published bundle and production observations separately.
