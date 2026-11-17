# Billing attribution and bounded collection

## Reconcile the bill

Create a meter table: product, billed units, included units, unit price, amount, currency, usage start/end and resource scope. Distinguish invoice issue date from consumption dates. Do not convert USD into EUR because the user described the bill in euros. Account for credits/tax separately from engineering savings.

Locate the actual plan and account-level allowances. Do not allocate the same free tier independently to every database or project. If only some resources are in scope, keep out-of-scope usage in the allowance model without changing those resources.

Gather comparable completed UTC days: before the spike, during the spike, after each relevant deployment. Record release timestamps, traffic changes, outages and cleanup jobs. A reduction caused by an outage or dropped uploads is not an optimization win.

## Collection order

1. Invoice and product-level totals.
2. Daily totals by resource, including reads, writes, storage, requests, CPU or relevant product units.
3. Top operation shapes by total units and count, with duration as a separate dimension.
4. Current schema, indexes, migrations and source-to-query mapping.
5. Small representative query-plan or metadata probes only where they answer a concrete uncertainty.

Use a service connector when it has sufficient capabilities; otherwise use established read-only credentials or the provider dashboard/API. Keep credential values out of command output, transcripts and artifacts. Saving encrypted query results does not make printing decrypted customer rows appropriate.

Prefer aggregates and normalized queries. Query text can contain identifiers, emails or other literals; inspect locally and redact before sharing. Apply query bounds and a collection budget, especially for already-expensive databases. A `LIMIT` does not guarantee a bounded scan; use the access path and plan to assess cost.

For D1 query analytics, consult the current GraphQL schema and product documentation. Adaptive analytics can estimate counts and sums; do not apply a second sampling multiplier without evidence that raw unweighted data requires it. A top-N result is not the whole database. Validate API errors even when HTTP is 200, pagination, account scope, dataset availability and UTC boundaries. An empty result is not zero usage.

Example query skeleton, to adapt against the current schema:

```graphql
query {
  viewer {
    accounts(filter: {accountTag: "ACCOUNT_ID"}) {
      d1QueriesAdaptiveGroups(
        limit: 100
        filter: {datetime_geq: "START_UTC", datetime_lt: "END_UTC"}
        orderBy: [sum_rowsWritten_DESC]
      ) {
        count
        dimensions { databaseId query }
        sum { rowsRead rowsWritten queryDurationMs }
      }
    }
  }
}
```

Run separate rankings for reads and writes. Verify `start < end`; wait for ingestion delay instead of manufacturing an empty or future window. Use the platform's available retention and resolution, not an assumed universal interval.

## Costs and forecasts

Label a database-only estimate as **D1 read/write usage**, never the total site bill. Maintain a meter checklist with measured, not applicable and unknown states for requests, CPU, logs, storage and shared services. Unknown is not zero. A seven-day window that excludes a monthly sweep cannot establish that sweep's monthly cost; measure its previous run separately or disclose the omission.

Attach collection time, dataset, resource scope and UTC window to reused evidence. Do not describe an earlier saved snapshot as freshly collected. Retain before/after evidence in separate files rather than overwriting the baseline during verification.

For an added index, compare saved read charges with additional write/storage charges and one-time migration cost. Compute account-level baseline and candidate costs across affected meters before subtracting. If recurring net savings are positive, payback time is migration cost divided by net recurring savings; otherwise there is no demonstrated financial payback. Do not infer index writes from query count alone. A large share of reads can still represent pennies, and a performance improvement may be worthwhile without being a cost-saving priority.

For a single linear meter with monthly included allowance:

```text
projected units = observed units / observed seconds * target seconds
overage cost = max(0, projected units - included units) / price-unit size * unit price
net savings = baseline overage cost - candidate overage cost
```

Apply storage, requests, CPU, operation classes and fixed fees separately. Use the actual billing period rather than universally multiplying by 30. If the pricing uses rounding, tiers, daily limits, minimum storage duration or custom contracts, the simple formula/helper is insufficient.

Separate four quantities:

- **Measured units saved per action** from controlled experiments.
- **Historical category ceiling**: the whole category's former spend, not all recoverable.
- **Modeled savings** based on stated volume/adoption assumptions.
- **Observed production savings** from comparable post-change traffic.

Do not add overlapping estimates: filtering an upload can also remove metadata and ledger writes already counted elsewhere. A small sample after one fix cannot be multiplied into an exact percentage for a different traffic population. Show scenarios and confidence, not fabricated precision.

At scale, separate fixed background work from per-active-device, per-session, per-upload and per-record work. Active owner keys are not necessarily paying customers. Model burstiness, retries and queue capacity as well as average monthly units.

The cost helper input uses arbitrary verified pricing, not built-in Cloudflare rates:

```json
{
  "meter": "example writes",
  "currency": "USD",
  "observed_seconds": 86400,
  "target_seconds": 2592000,
  "baseline_units": 4000000,
  "candidate_units": 2500000,
  "included_units": 50000000,
  "price_unit_size": 1000000,
  "price_per_unit": 1
}
```

These are illustrative inputs, not a statement of current pricing. Baseline and candidate must use the same observation duration and account scope. Normalize otherwise. Aggregate units before applying a shared allowance.

For executable collection, multi-meter growth/payback, cost-attribution remainder checks and incident timelines, use [the toolkit](toolkit.md). Keep collection receipts and model assumptions together; a model is not a substitute for provider evidence.
