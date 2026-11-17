# Database review beyond D1

Use when the project uses a database other than D1, directly or through a proxy/ORM. For D1, use [D1 patterns](d1-patterns.md). Inspect every database role: transactional source, cache, analytics store, search/vector index, replica and backup. A cache or ORM does not remove the underlying database's costs or consistency requirements.

## Identify the actual system first

Record engine, deployed version, managed provider/plan, region, driver/ORM, connection proxy, read replicas and source of truth. Read their current official documentation using the [sources checklist](sources.md). Unknown version or provider scope is an evidence gap. Compatibility with PostgreSQL/MySQL syntax is not proof of identical planning, transactions or billing.

| Family | High-value checks | Evidence needed before a change |
|---|---|---|
| PostgreSQL and compatible services | ORM N+1, selectivity and statistics, joins/sorts, wide reads, locks/long transactions, index maintenance, connection churn, replication and retained WAL | Emitted queries, appropriate plans and workload statistics; provider compute/I/O/storage/network meters. Confirm engine-specific index creation, maintenance and migration-lock behavior. |
| MySQL/MariaDB and compatible services | Composite index order, implicit casts/collations, range scans, deep pagination, locking, connection limits, replica lag and binlog retention | Version-specific query plans and statement metrics; engine/provider semantics for online schema changes and replication. Do not transfer SQLite planner assumptions. |
| Document/partitioned stores | Broad collection scans, unselective compound queries, cross-partition fan-out, hot partitions, denormalized write amplification and listener churn | Partition key distribution, actual operation/request units, query plans if supported, index policy and consistency needs. Document count is not a universal billing unit. |
| Redis-compatible/cache stores | Full key enumeration, hot or oversized keys, serialization, TTL churn, misses, eviction, replication/persistence and unnecessary round trips | Existing latency/memory/eviction/call metrics, access patterns and durability role. Cache loss can become data loss if the application treats it as authoritative. |
| Search/vector/analytics stores | Full rescans, unnecessary reindexing/re-embedding, high-cardinality aggregation, refresh frequency, stale copies and duplicate ingestion | Scanned bytes/partitions or actual product units, index/corpus growth, query distribution and quality/freshness requirements. |
| Proxy/pooling layer, including Hyperdrive | Pool churn/saturation, duplicated direct/proxied routes, cache misses and stale reads | Supported engine/driver, configured caching and connection lifecycle; attribute proxy and external provider charges separately. |

These are investigation prompts, not automatic instructions to rebuild indexes, vacuum, shard, partition or resize. Read-only statistics are preferable to creating expensive new instrumentation. Do not enable query logging containing secrets or customer payloads merely to finish an audit.

## Safe query-plan inspection

Use the engine's documented non-executing plan mode for initial inspection. **`EXPLAIN ANALYZE` can execute the statement**; it is not interchangeable with a plan-only query. Do not run mutating statements, volatile functions, heavy scans or locking probes against production as casual diagnostics. Even SELECT-based measurements may consume substantial resources. Use synthetic fixtures, existing aggregate statistics and bounded probes consistent with authorization. PostgreSQL's [EXPLAIN documentation](https://www.postgresql.org/docs/current/using-explain.html) describes this distinction; verify the deployed engine/version before choosing a command.

Validate changed queries on missing/null values, duplicates, tenant boundaries, collation, time zones, range boundaries, concurrent updates and deterministic pagination. Match production parameter types and realistic skew. If the proposed change affects replicas or caches, test read-after-write and transaction requirements. A fast stale answer is not equivalent to a correct fresh answer.

## Cost and capacity

Separate variable usage from provisioned/fixed costs. Reducing rows scanned on a fixed-size database may reduce latency or defer an upgrade without reducing today's bill. Claim a cash saving only when an actual billed meter falls or a validated resizing/plan change reduces spend. Include migration, backup, replication, external transfer and operational costs.

For scale, measure expensive tenants and hot partitions separately from averages. Estimate connections, burst concurrency and history growth as well as requests per second. Prefer the smallest proven change; sharding, materialized summaries, new cache layers or a VPS require explicit consistency, recovery and operational tradeoff analysis.
