# Proving fixes and shipping them

## Choose tests by the invariant

Use [the toolkit](toolkit.md) for matched SQLite workloads, retained-data hashes, regression thresholds and application failure-test requirements. Extend fixtures to the actual operation and use the correct runtime adapter before making provider-billing or concurrency claims.

| Change | Required evidence |
|---|---|
| Query rewrite | Same records, missing/legacy identities preserved, realistic skew, indexed plans and lower measured reads |
| Index addition | Exact definition, populated/skewed fixtures, unchanged join multiplicity and timestamps, indexed plans, added write/storage and migration cost |
| Index removal | Exact live definitions, no lost uniqueness/collation/ordering contract, consumer plans, insert/update/delete write counts |
| No-op UPSERT | Identical values produce no billed writes; changed and null fields still update; triggers inspected |
| Delta summary rebuild | Same derived rows, orphan removal, old-state repair, retention, identity merge and transaction rollback |
| Rate counter | Exact window boundary, limits, concurrency, cleanup races, one overall deadline, no retry after uncertain mutation |
| Upload batching | Durable queue, overflow, crash/restart, shutdown, retries, lost response and all record side effects |
| Archive | Full restore and query semantics, idempotency, partial failures, access controls and recoverable dual writes |

Run the source tests and the exact emitted runtime where transformations matter. Use the installed supported runtime/toolchain rather than silently adding dependencies. SQL stubs may reject a new valid query: reproduce the failure, update the fixture to model the new path faithfully, and keep all original assertions. Do not turn an integration failure green by bypassing authorization or returning unconditional success.

Targeted tests are not the complete release gate. Run the repository's broader required tests before declaring deployment-ready. On failures, distinguish real regressions, fixture gaps, unrelated baseline failures and environmental limits. Baseline comparison must use the same relevant toolchain and conditions. Do not fix unrelated failures without scope, and do not ignore mandatory gates.

Keep local and production evidence separate:

- Source review establishes intended logic.
- Node SQLite establishes selected SQL/result invariants.
- Local Workerd/Miniflare D1 establishes local runtime behavior and counters.
- Canonical bundle tests establish the emitted candidate's behavior.
- Provider readback establishes what is live.
- Production observation establishes actual usage/error effects in the stated window.

## Deadline review

Review all callers and the actual timeout helper. A timeout winner does not imply cancellation of losing promises. Check late continuation after both successful no-match and error outcomes. Preserve rejection even if a database write later commits.

A request-local active flag cleared when the outer operation settles can prevent a late continuation from beginning fallback. A pre-fallback elapsed-time check also covers a delayed timer callback. Neither reverses a write already submitted. Avoid broad helper changes when the fix belongs to one multi-step operation. Use the platform's documented time semantics and existing project conventions; do not assume the wall clock advances normally in every Worker context.

## Production preparation

1. Identify canonical deployment wrapper, account/environment, resource bindings, routes, schedules, migrations and rollback procedure.
2. Preserve unrelated work. Do not deploy unreviewed files simply because they share a working tree. If config changed, reconcile against live state through the guard; do not restore an older config that would retire valid admissions or bindings.
3. Build and test the canonical emitted artifact. Record its hash and exact scope. Preserve artifacts so publication can be compared byte-for-byte.
4. Capture current active version/traffic, binding values where nonsecret, secret names, schedules/routes and applied/pending migration inventory. Keep sensitive evidence local and access-controlled.
5. Review migration compatibility with current and rollback code. Index removal does not delete records, but can affect old query plans or explicit index references. Do not invent a rollback that cannot restore data or schema semantics.
6. Honor the user's authorized deployment scope. If authorization is missing, present the concrete tested result and ask only for the remaining action. Fresh Access exports, credential scopes or admission hashes required by a repository guard are real prerequisites; collect them through approved read-only paths instead of disabling checks.

## Deployment and readback

For a migration-only fix, use the repository's migration path; a Worker redeploy is unnecessary unless runtime/configuration also changed. List pending migrations immediately before applying them. If the command would include unrelated migrations, isolate the reviewed change through the supported workflow instead of applying everything. Verify both the migration ledger and actual index definition afterward: neither alone proves the other. Retain the production query plan and bounded read-only probe metadata. Rollback for an added nonunique index removes that index, not customer records; reconcile the migration ledger using repository conventions before any reapplication.

Use the guarded production path, including its pinned runtime and empty/controlled environment where required. Apply only reviewed migrations. After a timeout or uncertain publish response, inspect the active version before retrying; another deployment may have won.

Independently verify active version, intended traffic percentage, published bytes, retained bindings/secrets, schedules/routes, migration records and relevant live probes. A redirect to an authentication page proves access gating, not a successful authenticated admin workflow. An HTTP 200 is not sufficient if the response body is an error or the wrong version.

Do not generate abusive load or synthetic customer records in production merely to demonstrate savings. Use normal traffic first; controlled live write/load probes require appropriate explicit scope. Stop further rollout if deployment attribution is ambiguous, guard verification fails or unrelated configuration would be changed.

## Observation

Record activation time and wait for analytics ingestion. Reject inverted windows and exclude pre-deployment activity when attributing a new query shape. Compare units per successful action and error/retry rates before projecting totals.

Short samples can establish that a new operation shape appears and uses fewer writes. They cannot establish monthly cost, full error freedom or behavior at production-scale concurrency. Obtain a complete representative day, including cron cycles; use longer windows when weekly jobs or traffic seasonality matter. Do not claim ongoing monitoring was scheduled unless it actually was.
