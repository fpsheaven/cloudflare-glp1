# Authoritative sources to refresh during each audit

Prepared on 2026-11-16. This is a navigation list, not a snapshot of current tariffs or contractual guarantees. Open the relevant current pages and cite the precise claim used; record when live verification is unavailable.

## Mandatory documentation pass for agents

On each new audit or change, fetch and read the latest relevant official Cloudflare documentation and the actual database's official documentation before making platform-dependent findings. Previously read pages from the same task may be reused when still applicable; refresh when scope, deployed version or the underlying claim changes. Training knowledge, this skill's examples, cached notes and search snippets do not substitute for reading the source.

1. Identify Cloudflare products, database provider/engine, deployed version and compatibility settings from configuration or read-only introspection. Mark unknown versions explicitly.
2. Read current Cloudflare pricing, limits and APIs for the affected products. Read database/provider documentation for indexes, query planning, transactions, consistency, constraints and migrations as relevant to the proposed change.
3. For D1, read Cloudflare D1 plus SQLite docs and verify that the engine feature is supported by D1. For PostgreSQL, MySQL or another engine, use that engine's official versioned manual plus the managed provider's restrictions. Do not assume D1 rules apply to every database, or that the newest engine feature is deployed.
4. Check relevant release notes when behavior, support or pricing may have changed. Resolve moved links through official indexes. Prefer the newest documentation applicable to the deployed version over an unrelated latest-version manual.
5. Record `claim | official URL | retrieved UTC date | product/version | implication or unresolved gap` in the evidence ledger. Cite the supporting page beside the finding or recommendation. Tests complement documentation; neither proves unsupported provider semantics on its own.

If official pages cannot be accessed, state the specific gap. Continue findings independent of it, but do not describe the affected recommendation as verified or deploy it until the necessary semantics are established. Do not replace an unavailable official guarantee with a third-party blog.

## Billing and query measurement links

The linked [billing traps reference](documented-billing-traps.md) records specific decisions grounded in the expanded documentation review. The [whole-project workflow](whole-project-audit.md) defines coverage and final reporting.

- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/): included units, row/index billing and storage.
- [D1 expensive-query analysis](https://developers.cloudflare.com/d1/observability/find-expensive-queries/): operation-level attribution and adaptive analytics.
- [D1 metrics](https://developers.cloudflare.com/d1/observability/metrics-analytics/): resource counters and available observation methods.
- [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/): request and CPU meter definitions.
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/): operation classes, storage classes and retrieval terms.
- [KV pricing](https://developers.cloudflare.com/kv/platform/pricing/), [Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/), [Queues pricing](https://developers.cloudflare.com/queues/platform/pricing/): refresh only for products involved in the bill.

## D1 and SQLite behavior

- [D1 database/batch API](https://developers.cloudflare.com/d1/worker-api/d1-database/): transaction behavior and batch failure.
- [D1 prepared statements](https://developers.cloudflare.com/d1/worker-api/prepared-statements/): bindings and result semantics.
- [D1 result objects](https://developers.cloudflare.com/d1/worker-api/return-object/): metadata available for measurement.
- [SQLite UPSERT](https://www.sqlite.org/lang_upsert.html): conflict behavior, null-sensitive updates and SELECT parsing ambiguity.
- [SQLite query planner](https://www.sqlite.org/queryplanner.html): index prefixes, covering indexes and ordering.
- [SQLite CREATE INDEX](https://www.sqlite.org/lang_createindex.html): uniqueness, collations, partial indexes and name-based IF NOT EXISTS behavior.
- [SQLite AUTOINCREMENT](https://www.sqlite.org/autoinc.html): bookkeeping and ID reuse guarantees.
- [SQLite PRAGMAs](https://www.sqlite.org/pragma.html): index introspection and statistics maintenance; check D1 support before use.

## Runtime and operations

- [Workers GraphQL metrics tutorial](https://developers.cloudflare.com/analytics/graphql-api/tutorials/querying-workers-metrics/): supported metric query structure; confirm schema/entitlements in the target account.
- [Worker schedule API](https://developers.cloudflare.com/api/resources/workers/subresources/scripts/subresources/schedules/methods/get/): read-only schedule response shape.
- [D1 query API](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/): SQL endpoint and metadata; a POST request is not automatically a write, but only explicit read-only SQL belongs in audit collection.

- [Cloudflare product directory](https://developers.cloudflare.com/directory/): discover documentation for every configured product, including products absent from this skill's examples.
- [Queues batching and retries](https://developers.cloudflare.com/queues/configuration/batching-retries/): delivery attempts, acknowledgement and batch behavior.
- [Hyperdrive query caching](https://developers.cloudflare.com/hyperdrive/concepts/query-caching/) and [connection pooling](https://developers.cloudflare.com/hyperdrive/concepts/connection-pooling/): distinguish proxy/cache behavior from the origin database.

- [Promise.race](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/race): promise settlement semantics; do not infer cancellation.
- [Workers runtime limits](https://developers.cloudflare.com/workers/platform/limits/): request/runtime constraints.
- [Workers versions and deployments](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/): deployment attribution and traffic.
- [D1 migrations](https://developers.cloudflare.com/d1/reference/migrations/): migration lifecycle.
- [D1 Time Travel](https://developers.cloudflare.com/d1/reference/time-travel/): recovery capabilities and limitations.

If a link moves, use the official product documentation index. Do not silently substitute a third-party blog for a platform guarantee. SQLite documentation explains the engine; D1's supported interface and live runtime still require their own verification.

## Other database engines

Use these as entry points, then select the deployed version and managed provider. Read the detailed pages for the particular behavior under review; an overview is not evidence for an index, isolation or billing claim.

- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html): plan interpretation and the distinction between planning and execution; switch to the deployed version.
- [MySQL documentation](https://dev.mysql.com/doc/): versioned manuals and release notes; check MariaDB or other compatible engines against their own official documentation when applicable.
- [MongoDB query plans](https://www.mongodb.com/docs/manual/core/query-plans/): planner behavior and version-specific distinctions; managed-service billing requires separate provider documentation.
- [Redis operations documentation](https://redis.io/docs/latest/operate/): select the actual product/version and consult relevant persistence, memory, replication and operational guidance.

For other relational, document, graph, time-series, search or vector databases, locate the official engine/provider documentation rather than treating an unlisted database as unsupported or copying rules from another engine.
