# Documentation-backed decisions

Reviewed against Cloudflare documentation on 2026-11-16. Re-open these sources during an audit: plans, features and meter definitions can change. These rules refine attribution; they do not authorize product changes.

## Worker requests are not the same as every internal call

Under Workers Standard pricing, service-binding calls do not add another request fee, while CPU across the participating Workers still counts. Legacy pricing differs. Native static-asset delivery and Workers Caching also have different billing treatment: do not assume every static response is free or every cache hit removes a request charge. Identify the actual serving path and enabled feature before modeling it. [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)

Audit consequence: map the entry request and its subrequests once, then attribute downstream D1/R2/KV work separately. Moving a call behind a service binding is not proof of reduced database or CPU cost. Consolidating Workers solely to remove an imagined internal request fee can be pointless.

## Slow responses do not prove CPU spend

Worker wall time can include waiting and background work; it differs from CPU time and final response completion. An invocation marked successful is not necessarily a successful HTTP/business operation. Check CPU and wall distributions, outcome/status, response completion and retry rate separately. [Workers metrics](https://developers.cloudflare.com/workers/observability/metrics-and-analytics/)

Audit consequence: do not turn a network-latency finding into a CPU savings estimate, and do not interpret a drop in successful uploads as a cost win.

## D1 search shape and schema placement matter

A leading wildcard can prevent a normal B-tree index from helping substring search. FTS can change that tradeoff but introduces its own storage/write costs. Schema/index creation belongs in migrations rather than request-time work. Verify plans and rows read, especially the ratio of reads to returned rows. [D1 indexes](https://developers.cloudflare.com/d1/best-practices/use-indexes/)

Audit consequence: inspect dashboard search and COUNT queries alongside the polling paths. Do not add indexes indiscriminately or treat an index name as proof of a cheap access path.

## Queue batching does not turn many messages into one operation

Queues operations are per message and data-size chunk, not per delivery batch. The documented unit is 64 KB, with internal metadata contributing to size. Retries add reads and dead-letter handling adds work. Current pricing also includes a queue-count dimension. [Queues pricing](https://developers.cloudflare.com/queues/platform/pricing/)

Audit consequence: measure payload sizes near boundaries, retry counts, per-tenant queue proliferation and consumer CPU. Batch tuning may reduce invocation overhead without reducing message operations. Preserve acknowledgments and partial-failure behavior.

## Durable Object hibernation has conditions

The Hibernation WebSocket API can leave clients connected without accruing duration while the object sleeps. Outgoing WebSockets do not hibernate; timers and other activity can prevent hibernation. Reconstruct state correctly when the object wakes. [Durable Object WebSockets](https://developers.cloudflare.com/durable-objects/best-practices/websockets/)

Audit consequence: read constructors, alarms, timers and connection roles before recommending hibernation. Do not infer “idle costs nothing” merely because no application messages are visible.

## KV caches absence as well as values

KV is eventually consistent; remote visibility can lag by 60 seconds or more, including newly created keys after cached negative lookups. It is not an atomic read-modify-write transaction store. [KV consistency](https://developers.cloudflare.com/kv/concepts/how-kv-works/)

Audit consequence: moving counters, permissions or delivery state to KV may change correctness. Include missing-key behavior in any cache test, not just updates to existing keys.

## Cache API locality limits the savings model

Cache API content is local to the originating data center. `cache.put()` does not participate in tiered caching; the fetch path is used for that behavior. Deployment context also affects whether Cache API operations work. [Workers Cache API](https://developers.cloudflare.com/workers/runtime-apis/cache/)

Audit consequence: do not predict one global cache fill per key. Check geographically distributed cold misses, deployment environment and invalidation scope. Test privacy boundaries before caching authenticated data.

## Use cost controls as limits, not as proof of optimization

CPU caps, sampling, queue concurrency and retry limits can contain spend, but can also reject work or remove diagnostic history. Report these as operational/product tradeoffs. A lower bill produced by more failures is not a lossless reduction. For budget controls, specify the expected failure mode and preserve the user's chosen availability and data requirements.

## Read retry behavior is not write retry permission

D1 documents automatic retries for retryable read-only failures and bounded application retries for selected errors. Inspect every retry layer before calculating amplification. Application timeouts on a write can leave commit status unknown; the read-only retry policy is not permission to replay a counter increment or other non-idempotent write. [D1 retries](https://developers.cloudflare.com/d1/best-practices/retry-queries/)

Audit consequence: follow client, Worker, SDK and database retries separately. Distinguish a documented retryable rejection from an ambiguous completed mutation, and retain idempotency where needed.

## Invocation logs and application logs are separate sources

Workers Logs includes automatic invocation records as well as custom logs and errors. Inspect the actual environment's observability settings, head sampling and invocation-log configuration; do not count only explicit `console.log` calls in source. [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/)

Audit consequence: attribute logging spend before proposing suppression. Sampling requests can remove useful failures along with successes, so preserve the user's required evidence and do not present a sampling change as strict-lossless.
