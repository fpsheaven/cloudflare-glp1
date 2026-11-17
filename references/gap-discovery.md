# Systematic gap discovery

Use this reference for broad audits and requests to find more gaps. For a scoped fix, use only the rows relevant to that fix. This is an investigation map, not proof that any listed problem exists. Discover all products in use from source, configuration and permitted provider inventory; this list is deliberately extensible. Read current official product and database docs before assessing their behavior.

## Coverage states

For each applicable component and check, record one state:

- `finding`: evidence supports an issue; link a stable finding ID.
- `reviewed-no-finding`: inspected evidence supports no issue in the stated scope/window; not a guarantee about all traffic.
- `unknown`: relevant source, version, permissions or measurements are missing; name the smallest next check.
- `not-applicable`: evidence shows the feature/path is absent or outside the requested scope; record why.

A filename search with no matches does not justify `not-applicable`. A service may be configured in the dashboard, an external scheduler, generated code or another repository. Distinguish source coverage from live configuration and billing coverage. Do not use a single percentage to imply all three are complete.

Suggested working record:

```yaml
component: "client, route, job, database or product"
check: "one question from the matrix"
state: unknown
evidence: []
finding_ids: []
gap: "what is missing, if any"
next_check: "smallest useful inspection or measurement"
```

## Seven complementary passes

1. **Inventory outward:** follow clients to APIs, bindings, jobs and data stores. Include web/mobile/desktop/CLI clients, language-specific wrappers, generated deployment inputs and dashboard-only resources. Identify environment, tenant boundaries and owner. Do not assume everything in an account belongs to the audited project.
2. **Bill inward:** map each material invoice meter to resources and operation shapes, including fixed fees and external database/origin charges. Reconcile the unexplained remainder; an expensive line without source ownership is a gap even if SQL looks good.
3. **Trace normal work:** count invocations, fan-out and retained writes per useful user action. Include hot/cold keys, empty/nonempty responses, first/repeat requests and foreground/background behavior.
4. **Trace failure and recovery:** inspect timeouts, retries, duplicate delivery, partial success, reconnect, expiry and resume. Look for work repeated after a successful side effect or work continuing after its caller gave up. Use synthetic/local failure tests; do not inject faults into production without authorization.
5. **Trace time and growth:** review hourly/daily/monthly jobs, retention, accumulated history, low-traffic periods, bursts and tenant skew. Separate work proportional to users, records, elapsed time and Cartesian combinations. Forecast more than one growth driver rather than multiplying every meter by the same factor.
6. **Reconcile deployed state:** compare source intent with published artifacts, bindings, schedules, schema, indexes, cache rules and old environments. An unused-looking resource needs ownership/consumer evidence before recommending retirement. Do not delete it during an audit.
7. **Challenge findings and close gaps:** check whether current caching, coordination or a previous fix already eliminates the suspected work. Identify the evidence that would disprove each important finding. Merge duplicates that share a root cause, avoid overlapping savings, and revisit pending in-scope components after finding the first expensive query.

## Gap matrix

For every applicable row, trace an actual caller, inspect relevant source/configuration and name the observation that would confirm or reject a finding. Read the detailed references only for the products encountered.

| Area | Questions that expose gaps | Evidence and preservation check |
|---|---|---|
| Billing and resource ownership | Wrong account/period/currency? Shared allowances counted repeatedly? Legacy plans, subscriptions or abandoned paid resources? | Invoice, current plan, resource owner, daily totals and credits. Plan changes need feature/limit and contractual comparison; never assume cancellation is harmless. |
| Clients and SDK wrappers | Duplicate effects/listeners/timers? Multiple tabs/devices doing identical work? Tight reconnect or retry loops? Old client versions still active? | Trace lifecycle cleanup, visible/hidden/offline/resume paths, rollout adoption and actual cadence. Preserve delivery and freshness contracts. |
| HTTP/API/GraphQL | N+1 calls, redundant hydration, recursive fetches, duplicate prefetch, wide list responses or unbounded pagination? | Count downstream calls per action and inspect query complexity/page limits. Do not remove required validation or fields consumers use. |
| Workers and origin compute | Repeated parsing, allocation, compression or transforms? Whole-body buffering? Idle/background work? Work continuing after disconnect? | Separate CPU, wall duration, memory and external latency; inspect distributions rather than only averages. Maintain streaming/error/cancellation guarantees. |
| Cache layers | Fragmented keys, unnecessary user/cookie/query variation, ignored cache directives, stampedes or duplicate refresh? Cache misses in every region? | Follow browser, CDN, Worker, proxy and database caches independently. Verify invalidation, authorization, tenant isolation, stale reads and cache-bypass behavior. |
| SQL reads | Missing or unsuitable indexes, join expansion, repeated aggregates, leading-wildcard filters, type casts, deep offsets or ORM lazy loads? | Exact emitted SQL, representative plans, cardinality/skew and measured scan cost. Preserve nulls, duplicates, collation, tie order and pagination. |
| SQL writes | No-op updates, index amplification, trigger/cascade fan-out, full-summary rebuilds or duplicated audit records? | Trace one business mutation through all effects; compare retained state and provider counters. Preserve timestamps, constraints and audit requirements. |
| External databases and connection pools | Connections opened per action? Unbounded pools? Long transactions, locks, repeated failovers, overprovisioning or replica lag? | Use [database review](database-review.md); inspect provider compute/I/O/storage/transfer costs and consistency, not D1 rates. |
| KV and key caches | Whole-namespace listing, hot keys, cache-miss fallback, identical writes or short TTL churn? | Operations per key, hit/miss distribution and consistency contract. Do not replace a coordinated store with an eventually consistent one by assumption. |
| R2/object storage | HEAD-before-GET, repeated LIST scans, tiny-object churn, duplicate uploads, abandoned multipart work or unused derivatives? | Operation classes, size distribution, lifecycle and retrieval costs; preserve download integrity, pointers, restore and access policies. |
| Queues and webhooks | Batch retries replay successes? Poison messages? Missing deduplication? Retry layers multiply attempts? Dead-letter buildup? | Trace acknowledgement, retry budget, idempotency and side effects end to end. Preserve delivery, ordering and recovery; never turn failure into a success ACK to lower costs. |
| Durable Objects and realtime | Keepalives preventing useful idle behavior? Excess alarms, reconnect fan-out or one hot coordinator? | Requests, duration, storage, wakeups and per-object skew. Assess applicable hibernation rules and preserve session state/coordination. |
| Cron, Workflows and reconciliation | Overlapping schedules? Jobs scan everything when nothing changed? Repeated successful steps? Missing checkpoint, lock or watermark? | Inspect cadence, resumability, lease ownership, incremental boundaries and catch-up behavior; include monthly/seasonal runs. |
| Retention, backups and analytics pipelines | Duplicate copies, whole exports, historical reprocessing, snapshots never retired or untested archive restore? | Volume and change rate, retention policy, RPO/RTO and restore evidence. Do not shorten history or backups merely because old data is costly. |
| Logs, traces and metrics | Duplicate sinks, payload-heavy successes, excessive span/cardinality volume, scans of all logs for each alert? | Read ingestion/query/storage/export meters and useful signal requirements. Filtering/sampling is a data tradeoff; preserve failures and required audit trails. |
| AI, embeddings and search | Re-embedding unchanged documents? Duplicate generation, unbounded context/output, retrying paid calls or rebuilding indexes? | Model/provider units, task quality, corpus changes, retrieval filters and downstream charges. Caching/model changes require privacy, freshness and quality checks. |
| Images, video and browser workloads | Repeated transformations, unbounded variant keys, duplicate media copies, leaked sessions or rendering on every request? | Product-specific units, lifecycle, formats/variants and cache behavior. Preserve visual quality, accessibility, session isolation and necessary outputs. |
| Containers, builds and previews | Idle instances, duplicate build triggers, missing build cache, retained environments or old schedules still running? | Instance/runtime/build/storage meters and owners; check dependency, release and rollback needs before suggesting retirement. |
| Network and external services | Repeated cross-region transfers, external egress, expensive origin fallback, duplicated API calls or polling metered vendors? | Trace each network hop and vendor invoice separately; avoid double-counting internal requests. Include latency, residency and availability requirements. |
| Traffic and cost controls | Bots, accidental public expensive routes, abusive fan-out, retry storms or no visibility into spend changes? | Existing privacy-safe traffic evidence and current quotas/alerts/limits. A high bill alone is not proof of attack. Budget alerts are not assumed hard caps; new limits can reject legitimate work. |
| Configuration and environments | Schema drift, old bindings, scheduled previews, cache rules absent from source, stale deployed clients or missing release attribution? | Read-only provider comparison and migration history. Avoid declaring an undeployed source fix a live improvement. |

## Turn breadth into useful findings

Classify findings by **cost, performance, scale, reliability, data correctness, or evidence/operations gap**. One item may have multiple benefits, but do not give every category a dollar saving. Prioritize credible recoverable spend and practical user impact, not finding count. Low current cost with a demonstrated growth multiplier is a scalability finding; a missing metric is a measurement gap, not proof of waste.

Record prerequisites and interactions: caching may remove requests already counted under query optimization; an index can add writes; pushing updates can introduce persistent connection costs. Keep architectural options distinct from surgical fixes. Include what should remain as-is and why.

For small projects, apply this as a short checklist. For large projects, retain the coverage ledger and finding IDs across context boundaries and continue pending work without rescanning reviewed files. Stop broadening at the requested project boundary, not at the first finding. When access genuinely blocks completion, deliver supported findings and a concrete gap list; never claim exhaustive coverage or invent a fixed number of issues.
