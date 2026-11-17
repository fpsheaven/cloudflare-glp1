# Executable audit toolkit

Read this when collecting evidence, proving a change, forecasting scale, setting regression checks or evaluating the skill itself. Helpers use Python 3.10+ standard library. Run from the skill directory, replace `python` with the installed interpreter when necessary, and use output paths outside the distributable skill. Never include collected account artifacts in a shared ZIP.

## 1. Read-only evidence collector

`scripts/collect_evidence.py` builds a fixed request plan for explicit D1 databases and Workers. It collects D1 daily read/write usage, schema/index/trigger definitions, Worker request/error totals, deployment versions and cron schedules. It does not enumerate unknown accounts, load local credential files, fetch Worker secret values, query customer tables or accept arbitrary SQL/URLs. Database schema may itself contain sensitive defaults: keep the bundle private.

```text
python scripts/collect_evidence.py examples/collection.json
python scripts/collect_evidence.py MY_COLLECTION.json --live --output NEW_PRIVATE_DIRECTORY
```

First adapt the example account/resource IDs and complete UTC dates. Supply an existing appropriately scoped token through `CLOUDFLARE_API_TOKEN` without printing it. Dry-run is the default and makes no requests. `--live` is an explicit execution step within the user's authorized read-only scope, not authorization to mutate production. D1's SQL endpoint uses POST for the hardcoded schema SELECT; GraphQL requests contain queries only.

The collector has per-request time/size limits, a 20-resource cap, bounded datasets, no redirects and no automatic retries. New output directories prevent overwriting baselines. Manifest entries include collection times, SHA-256 hashes, unavailable datasets, missing-day and truncation gaps. Missing permissions, schema drift and API errors remain gaps, never zero usage. Adapt provider queries against current official docs if the schema changes; do not silently widen permissions or scope.

Live adapter schemas must be verified in the target account. Fixture-based tests exercise handling, not live provider compatibility. Invoices, allowances, CPU distributions, logs, other products and external databases require separate bounded evidence. Reconcile invoice meters against attributed amounts and explicitly list the unexplained remainder in the report. Do not present the default bundle as a complete bill or complete deployment snapshot.

For a numerical remainder check, run `python scripts/audit_models.py reconcile ATTRIBUTION.json`. Input fields are `currency`, `period`, `total_cost` and `attributed: [{"id":"database", "cost":60}]`. All amounts must use the same period, currency and tax/credit basis. The tool flags unexplained amounts and over-attribution; it cannot establish that the source mapping is correct.

## 2. Matched benchmark runner

```text
python scripts/benchmark_sqlite.py examples/sqlite-workload.json --output BENCHMARK.json
```

The runner creates independent in-memory databases for baseline and candidate. Each case defines identical `schema`, `seed`, `preserve_tables` and named `steps`; only `baseline_setup`/`candidate_setup` and optional variant command lists differ. `commands` is the shared default. Each command contains `sql` and optional `params`. Each step is one transaction. `expect_error` names the numeric SQLite error code expected for a failure test; the runner rolls back that step. Ordering is preserved unless `ordered:false` explicitly declares a result to be a multiset.

Use `--output NEW_FILE.json` on the benchmark/model CLIs to write UTF-8 evidence without shell-redirection encoding differences. Existing files are refused so later verification cannot overwrite the baseline.

It alternates variant order, repeats each case, records median local elapsed time, SQL VM instruction counts, SQLite change counts and query plans, and compares result hashes and retained-table hashes after each step. It checks initial data equivalence and detects nondeterministic outcomes. ATTACH/DETACH, SQL extension loading and PRAGMAs inside fixtures are denied; SQL and result work are bounded. Fixtures are trusted synthetic code, not a sandbox for hostile inputs.

The supplied workload covers present/absent/null keys, fresh/repeated queries, retained timestamps, duplicate delivery records, partial transaction failure and rollback recovery. Add skewed/high-volume cases representing the actual application. Do not use customer data to manufacture public fixtures.

**Limits:** VM instructions are not D1 rows; SQLite changes are not billed writes; local wall time is not Worker CPU. A fresh in-memory database is not a production disk-cache experiment. Engine transaction rollback is not end-to-end delivery recovery. For actual D1 costs, run the equivalent fixture under the repository's local Workerd/D1 harness and capture `meta.rows_read`/`meta.rows_written`. Other databases need their own documented engines and adapters.

## 3. Data-preservation and application failure tests

Treat the benchmark's `equivalent` result as evidence only for included SQL cases. Application tests must also exercise the exact timeout/retry/queue implementation:

| Scenario | Required assertion |
|---|---|
| Retry after acknowledged commit | One logical record and one required external side effect |
| Lost response after commit | Retry is idempotent; existing success is not treated as a new action |
| Failure between database and external side effect | Recovery converges without lost delivery or duplicate charge |
| Concurrent missing-key updates | No lost increments or duplicate logical identity |
| Timeout then late completion | No unauthorized fallback/replay; rejected request stays rejected |
| Cleanup races and clock/expiry boundary | Correct ownership/window semantics and no loss of pending work |
| Crash with a bounded client journal | Required data survives restart or the documented tradeoff is explicit |

Use deterministic barriers, controllable clocks and fault injection in a local test environment. Record seed, runtime, fixture hash, affected tables/outputs and failed assertions. Do not claim these application guarantees from a SQL-only pass; retain a `not-tested` entry until the application adapter exercises them.

## 4. Growth and break-even calculator

```text
python scripts/audit_models.py forecast examples/growth.json
```

Each meter represents one independent allowance pool. Supply explicit current prices (the example uses invented prices), an allowance, constant other-account usage, and baseline/candidate terms. Terms have period-normalized `units` and named growth-driver powers; omitted drivers stay fixed, so monthly jobs are not multiplied by user growth. Scenarios provide every referenced factor. Model busy customers/history as separate terms or scenarios.

The model combines all meter costs and fixed costs, deducts migration cost from first-period savings and reports financial payback only for positive recurring savings. Use separate currency/period runs rather than mixing them. Tiered pricing, rounding, transfer tiers, changing allowance pools and time-varying adoption require an extended model. Overlapping changes must already be combined in candidate volumes.

## 5. Cost-regression gates

```text
python scripts/audit_models.py regression BENCHMARK.json
```

Add explicit per-observation `rules` with `id`, `metric` and `max_ratio`, `max_delta` or `max_value`. The example already includes gates. Baseline/candidate fixture hashes and environment must match, observation IDs must match, equivalence must be true, and each required measurement must exist. A zero baseline permits no positive value under a ratio-only gate; use an absolute allowance when appropriate.

Exit 0 means supplied gates passed; exit 1 means a regression/equivalence failure; exit 2 means invalid or incomplete evidence. CI must fail on either nonzero exit. No silent passing on missing metrics. Prefer stable work counters for routine tests; timing needs adequate repetitions and agreed noise tolerance. An adapter may supply D1 row or Worker CPU counters in the same `observations[].metrics` schema, but include the exact runtime and units in `environment`. Do not mix SQLite proxy counts with provider counters.

## 6. Incident timeline analysis

```text
python scripts/audit_models.py timeline examples/timeline.json
```

Input nonoverlapping UTC/offset-aware buckets with summed operation `units`, `successful_actions` and `errors`; events carry `id`, `at` and `kind`. Supply deployments, migrations, cache changes, client releases and traffic incidents. Only full buckets inside each before/after window are included. The output marks incomplete windows, shows errors and units per successful action, and lists nearby confounding events. Zero successes yield unknown normalized cost, not zero.

Use matching tenants/actions and representative seasonal periods. Never sum percentiles or precomputed rates as units. The tool establishes temporal association, not causality; no automatic alerting or ongoing monitoring is installed.

## 7. Skill evaluation benchmark

Give an evaluating agent only `SKILL.md`, its routed references and one folder under `evals/cases/`. Use the folder's `TASK.md` as the request. Do not include `evals/rubric.json`, expected findings or previous answers. Respect the environment's delegation rules; this package does not itself grant permission to spawn agents or invoke paid models.

Afterward, an independent reviewer reads the actual answer against the rubric. Create scoring JSON with `cases`: each contains `id`, `expected` issue IDs, adjudicated `reported` issue IDs, lists of `unsafe_actions` and `unsupported_savings`, and boolean `has_improvement_list`.

```text
python scripts/audit_models.py score REVIEWED_ANSWERS.json
```

The scorer reports missed issues, false positives, precision, recall, unsafe actions and unsupported claims separately. Candidate measurements labeled uncertain are not automatically false-positive defects. Review the rubric's required reasoning manually; keyword matches and finding count are inadequate. Keep clean/no-finding cases to discourage invented problems. The current three synthetic projects cover a missing index, ambiguous delivery retries and a fixed-cost healthy database. Extend cases after real failures without embedding private evidence.

## Maintenance checks

Run both `scripts/test_helpers.py` and `scripts/test_audit_tools.py`. These test tool behavior with synthetic fixtures and mocked provider responses. They are not an independent evaluation of an LLM, a live Cloudflare integration test or proof of customer workload equivalence. Record those validation levels separately in reports.
