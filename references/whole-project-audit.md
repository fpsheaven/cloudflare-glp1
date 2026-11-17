# Whole-project cost investigation

The objective is to understand every first-party component well enough to explain how it contributes to Cloudflare usage. Do not stop after finding one expensive query, and do not confuse keyword matches with a completed review.

Use [systematic gap discovery](gap-discovery.md) throughout broad reviews. The file ledger tracks what was read; its gap matrix tracks which questions were answered. Complete both, including normal, failure, growth and deployed-state paths. For non-D1 stores, use [database review](database-review.md) instead of transplanting D1 pricing or SQLite semantics.

## 1. Establish scope and maintain a coverage ledger

Start with repository instructions, tracked and untracked files, workspace manifests, dependency manifests, deployment configuration, CI and infrastructure definitions. Use `rg --files` and version-control inventory first. Check whether ignore rules hide first-party services or generated deploy inputs; do not indiscriminately read ignored credentials, archives or build caches.

Create a working ledger with these fields:

| Component/path | Purpose | First-party files reviewed/total | Entrypoints and callers | Cloudflare products | Status/gap |
|---|---|---|---|---|---|
| Browser client | Customer interactions | Record actual coverage | Timers, buttons, reconnects | Calls API Worker | Reviewed or concrete remaining files |
| API service | Request handling | Record actual coverage | HTTP, RPC, webhooks | D1, KV, R2 | Reviewed or gap |
| Scheduled job | Periodic maintenance | Record actual coverage | Cron, alarm, external scheduler | Database/storage | Reviewed or gap |

Classify every discovered file/component as reviewed, excluded with reason, or pending. Read all in-scope first-party source/configuration, not just files that mention Cloudflare. For large files, record reviewed ranges and continue until complete. Inspect dependencies' behavior when a first-party call relies on it, without claiming to audit every vendored library.

Reasonable exclusions include dependency trees, binary assets, build caches and duplicate generated output. Generated deployment files are not excluded from artifact-parity checks. Tests and migrations are first-party evidence: read them for schema history, retries, intended behavior and missing coverage. Documentation may identify an external scheduler that code searches miss.

If the project spans repositories, identify the boundaries from manifests, imports and deployment references. Inspect locally available in-scope repositories. Record unavailable components and continue independent work. At completion, report explicit coverage such as “all 12 first-party components reviewed; external payment watcher unavailable.” Never claim to have read material you only listed.

## 2. Map triggers, paths and billed effects

### Starting from a public URL

Trace the page's actual API hosts and deployed route ownership before choosing a repository. The storefront, API and admin interface may live in different checkouts. Distinguish canonical source from historical theme snapshots; do not edit a snapshot merely because its filename matches the page.

A public HTML fetch blocked by a challenge is a coverage gap, not evidence that the product is broken. Continue through available source, bindings and provider metrics. A successful web-tool rendering does not establish deployed JavaScript parity. Record inaccessible runtime source separately from source inspected locally.

Do not silently turn a requested whole-project review into a hot-query review. Finding the dominant meter is an early result: continue available in-scope coverage. If access prevents completion, label the delivered review partial, list the missing files/services/meters and state which conclusions remain supported.

Build a call graph per product action:

```text
trigger -> client/wrapper -> Worker route -> service calls -> queries/objects/logs -> retry/ack
```

Include startup, idle state, foreground/background transitions, reconnects, errors, retries, shutdown and periodic jobs. Read scheduling and backoff code in every client language. A cheap route may become expensive because each open tab or device calls it repeatedly. A single UI action may trigger duplicate subscriptions or repeated effects.

Record each operation in a working table:

| Trigger | Cadence or volume driver | Fan-out | Per-call billed units | Failure/retry path | Retained data |
|---|---|---|---|---|---|
| Idle poll | Every N seconds per active client | Identity lookup + message lookup | Measure reads/writes/requests | Reconnect or timeout retries | Message state and timestamps |

For every outbound operation, identify the actual resource/environment and whether it is on the bill under review. Distinguish service bindings from public HTTP calls, local cache hits from network requests, and build-time tasks from live traffic. Follow wrappers until the real SQL/API call is visible.

Useful search terms, adapted to the project's languages:

- Configuration: `wrangler`, `cloudflare`, `d1_databases`, `r2_buckets`, `kv_namespaces`, `durable_objects`, `queues`, `crons`, `observability`, `run_worker_first`.
- Triggers: `scheduled`, `queue`, `alarm`, `setInterval`, `setTimeout`, `sleep`, `poll`, `heartbeat`, `retry`, `backoff`, `waitUntil`, subscriptions and lifecycle hooks.
- Work: `prepare`, `batch`, `exec`, `SELECT`, `UPSERT`, `INSERT`, `UPDATE`, `DELETE`, `COUNT`, `GROUP BY`, `ORDER BY`, `OFFSET`, `LIKE`, `get`, `put`, `head`, `list`, `fetch`, RPC.
- Volume: pagination, loops over users/records/objects, per-item awaits, repeated serialization, full-body reads, logs and payload sizes.

Search terms will have false positives and miss dynamically constructed operations. Read the surrounding functions and callers. A route name or function name is not evidence of its runtime behavior.

## 3. Read all subsystems, investigate expensive ones deeply

Perform a complete first-party source pass, then deepen evidence around plausible cost multipliers:

- Foreground and background client timers, multi-tab behavior, duplicate requests and offline recovery.
- Every deployed request handler, scheduled handler, queue consumer and Durable Object alarm.
- Identity/auth wrappers that run before otherwise-cheap operations; preserve security guarantees.
- All schema/migration/index history and live schema differences.
- Admin dashboards, exports, search, support tools and internal investigations.
- Retention, archive, reconciliation, backfill and cleanup jobs, including no-work runs.
- Deploy/build pipelines, preview environments, abandoned scheduled resources and environment drift.
- Error paths, retries, idempotency, dead-letter handling and notification/log amplification.
- Object/key listing, metadata refresh, small-object churn and cache invalidation.

For each component, record either supported findings or “reviewed; no evidenced cost issue.” Do not manufacture findings to make the audit look comprehensive. Keep useful low-cost work even if it appears frequently in a search.

## 4. Join source findings to billing evidence

Map query fingerprints and request/job metrics back to the operation table. Check whether enough shapes are collected to explain the dominant billed category. Label the unaccounted remainder. Query counts, sampled analytics and invoice units may not reconcile exactly; explain scope, sampling and time differences instead of forcing totals to agree.

Compute the important multipliers:

```text
trigger frequency × active producers × fan-out × retry amplification × units per operation
```

Then account for shared allowances and fixed fees. Use actual user/device/session counts rather than equating identity keys to paid customers. Separate growth in user count from growth in records per user: a query scanning all history can become more expensive per customer over time.

Without metrics, identify source-proven repeated work and provide scenarios with explicit assumptions. Label “needs usage measurement” instead of claiming a dollar amount. Ask only for missing data that materially changes prioritization; continue reading the project while waiting.

## 5. Prioritize changes the user can act on

Rank confirmed recoverable cost first, then confidence, data/behavior impact, effort and operational risk. Do not invent a numerical priority score if its inputs are unknown.

Group recommendations into:

1. **Change first:** demonstrated unnecessary work with clear preservation tests.
2. **Measure next:** credible source finding whose traffic or benefit is not yet known.
3. **Larger redesign:** archive, push delivery, cache, storage or infrastructure changes requiring new guarantees.
4. **Keep as-is:** low-cost or necessary work whose removal would cost more in reliability than it saves.

For each change, give the user an ordinary-language reason and a developer pointer. Example: “The catalog search examines many unrelated records. Use a verified lookup strategy that reduces scanned records while preserving search results and ordering.” State the measured workload and evidence rather than treating this hypothetical example as a finding.

## 6. End with a readable decision

The final answer should stand on its own:

```text
Most of the avoidable cost comes from [measured cause].

Keep [necessary feature]; its measured cost is small / it protects [requirement].
Confidence: [what was measured and what is estimated].
Coverage: [components reviewed and concrete gaps].
Status: [report only / patched locally / deployed and verified].

Things to improve, in priority order:
1. [Plain action] — [why it helps]. [Expected saving or unknown]. [Data/behavior impact]. Next: [specific action].
2. ...
```

Keep the final summary short enough to understand without reading SQL. Link a detailed report containing the coverage ledger, source references, measurements, docs and test evidence. When there is no confirmed waste, say so and identify the next measurement; do not promise a lower bill just because code can be changed.
