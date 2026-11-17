# Triage beyond D1

Use this reference when another billed meter dominates. These are investigative leads, not universal changes. Verify current product semantics, prices and account entitlements before conclusions.

For a broad review, use the [gap matrix](gap-discovery.md) even when one meter dominates, so lifecycle and cross-service issues are not omitted. This table routes product investigations; it is not an exhaustive catalog.

Read [documented billing traps](documented-billing-traps.md) before translating this inventory into savings. A whole-project scan must include every product actually configured, including products not listed below; consult their current pricing and runtime docs.

| Meter | Inspect | Preservation constraint |
|---|---|---|
| Worker requests | Client polling cadence, retry storms, scheduled invocations, service calls and bot traffic | Fewer requests must preserve delivery latency, authorization and freshness contracts. Determine which request classes are actually billed. |
| Worker CPU | Per-request CPU distribution, repeated parsing/crypto/compression, large transforms and accidental loops | Wall-clock duration is not CPU time. Do not remove signature verification or validation to save CPU. |
| Workers logs/observability | Invocation logs, success-event volume, duplicate application logs, retention and sampling | Errors, audit requirements and useful task results may need full fidelity. Log sampling changes data. Avoid adding verbose instrumentation that causes a second bill spike. |
| R2 | Object count/size, Class A/B operations, HEAD/LIST loops, duplicate uploads, lifecycle and storage class | Include operation costs, retrieval and minimum-duration rules where applicable. Preserve manifests, indexes, restore paths and access policy. |
| KV | Repeated gets/listing/puts, TTL behavior, identical payload writes and fallback patterns | Eventual consistency and cache staleness may change behavior; do not use KV as an equivalent transactional counter without proof. |
| External databases, Hyperdrive and pools | Emitted ORM queries, pool lifecycle, query caching, connection limits, replicas and external provider billing | Use [database review](database-review.md). Preserve transaction/read-after-write requirements and separate provider, proxy and transfer costs. |
| Durable Objects | Request volume, duration, storage, alarms and connection lifecycle | Keep ordering, coordination and wake-up behavior. Assess supported hibernation against the actual application. |
| Queues | Produce/consume/retry volume, batch fill, poison messages and dead-letter routing | Confirm retry/idempotency and retention guarantees. Fewer operations must not silently discard failed messages. |
| Cache/origin | Cache-hit ratio, cache keys, bypasses, revalidation and duplicated origin fetches | Avoid caching personalized or authorized responses across users. Preserve invalidation and private-cache rules. |
| Images, Stream, AI or other products | Product-specific usage units and resource ownership | Route to current product docs; D1 savings do not explain a different invoice line. |
| Containers, Workflows, Builds, browser workloads or vector services | Idle/running lifecycle, repeated steps, rebuild triggers, browser sessions, embeddings and index/query volume | Identify the actual product meters and downstream charges before proposing limits or migration. Preserve task completion, artifact provenance and result quality. |

## Scaling decisions

Fix proven pathological work before proposing infrastructure migration. Compare steady state, bursts, migration work and operational burden. Model usage per actual business action: completed task, session, retained record, message or active device.

For archive options, compare compressed batches plus query metadata against individual objects, including writes, reads, retrieval and indexing. Preserve ability to search, export and restore; object-store-plus-database dual writes need a recoverable protocol, not an assumed cross-service transaction.

For a VPS, include backups, monitoring, restore drills, patching, database maintenance, capacity, redundancy and incident ownership. Do not compare an all-inclusive managed bill against only a virtual machine's sticker price. An inexpensive VPS is an option only after the workload and required guarantees are understood.

## Suspicious traffic versus application waste

Separate customer use, internal jobs, retries and unwanted traffic using existing privacy-safe metrics. A high bill is not proof of an attack. If abuse is confirmed, scope any mitigation to documented traffic and preserve legitimate access. Do not turn a cost audit into broad security policy changes without authorization.
