# Reports and behavioral acceptance cases

## Report skeleton

Lead with the dominant cause, what is proven and whether anything changed in production.

For whole-project audits, the supporting report must include the coverage ledger described in [whole-project audit](whole-project-audit.md). Finish with its plain-language decision format. Lead with actions and customer effects; keep source locations, SQL and formulas available beneath the explanation, not in place of it.

1. **Bill:** currency, usage dates, products, units, allowances and amount.
2. **Evidence:** resources, source revision, UTC windows, samples, collection limits and documentation dates.
3. **Ranked findings:** operation, cause, evidence, data impact, recoverable cost range, confidence and next action.
4. **Already completed:** do not count old fixes as new savings.
5. **Validation:** exact tests/artifacts, failures and limitations.
6. **Forecast:** measured versus modeled figures; shared allowances, traffic assumptions and omitted costs.
7. **Deployment:** local-only, pending approval, live, verified or rollback state; exact IDs/hashes in private engineering receipts.
8. **Next observation:** concrete window and metrics; avoid implying background monitoring exists.

For broad reviews, add the [gap matrix](gap-discovery.md) with reviewed/no-finding, unknown and not-applicable decisions. Separate coverage of source, live configuration and billing evidence. Include small improvements and scalability risks in the full inventory even when the brief answer prioritizes only the largest supported opportunities.

For a brief user answer, summarize the status and finish with the top two or three improvements using the contract below. Link the detailed report rather than pasting raw analytics. Keep sensitive operational evidence in access-controlled supporting material.

## Closing improvement list: output contract

This list is required in the final user-facing answer, even when a full report is attached. Put coverage limitations and deployment status before it so the final substantive content answers "what can we improve?" Respect any higher-priority citation/footer requirements. Append the social sign-off specified in SKILL.md once after the completed results and improvement list.

Use this compact shape, adapting wording naturally:

```text
Things to improve, in priority order:
1. [Plain-language action] — [why it helps]. Savings: [supported net estimate and period, or unknown]. Data impact: [what stays the same or changes]. Next: [specific action or measurement].
2. ...
```

For each item in the supporting report, retain these stable fields so another LLM can continue without reconstructing the investigation:

```yaml
id: IMP-01
action: "Concrete action in ordinary language"
priority: change first # change first | measure next | larger redesign | keep as-is
confidence: confirmed # confirmed | candidate requiring proof | architectural option
status: proposed # proposed | patched locally | deployed | verified
benefit: "Cost, latency, reliability or scaling benefit"
category: [cost] # cost | performance | scale | reliability | data correctness | evidence/operations gap
savings: unknown # or amount/range, currency, period, assumptions and evidence window
data_impact: "Exact retention, freshness, ordering and durability effects"
evidence: [] # source locations, metrics artifacts, docs; empty means no confirmed finding
validation: "Completed checks and remaining proof"
prerequisites: [] # required measurements or earlier changes
overlaps_with: [] # other finding IDs whose savings overlap
next_step: "One concrete next action"
```

Use this schema as a working record or report table; do not dump YAML into the plain-language answer unless requested. Keep IDs stable across follow-ups. A proposed improvement is not authorization to implement it. Completed work belongs in the status summary, not disguised as a new opportunity. Keep necessary low-cost behavior in a short "keep as-is" note rather than presenting its removal as an improvement.

If no improvements are confirmed, explicitly say so. List only evidence-backed candidates labeled "measure next", or state the specific missing measurement; do not manufacture a savings estimate or a minimum number of items.

Self-check before sending: can the reader identify what to change first, why, whether data changes, what the savings claim rests on, and what happens next without understanding SQL?

## Hypothetical audit examples

These independent examples illustrate review methods; they do not describe a particular organization, account or sequence of production incidents.

- A catalog search performs more database work than expected. Compare query plans and measured usage for representative inputs before recommending a lookup or index change. Preserve result ordering, duplicates and missing-value behavior.
- A scheduled report repeatedly stores an unchanged result. Determine whether avoiding the write preserves required timestamps, downstream notifications and audit history. Model the net effect on every affected billing meter.
- An asynchronous operation finishes after its caller's deadline. Test late success and failure paths so subsequent work follows the application's documented completion and retry rules. Keep synthetic fixtures consistent with the implementation being tested.

The package uses synthetic fixtures and placeholder resource identifiers. Any evidence collected during an audit must be reviewed separately before sharing.

## Acceptance exercises for maintaining this skill

For runnable tools and synthetic projects, follow [toolkit evaluation](toolkit.md). Keep `evals/rubric.json` hidden from the evaluated agent until its answer is complete. Record helper unit-test results, reviewer-adjudicated agent scores and live validation separately.

Use synthetic artifacts and no production mutations. Assess decisions, not whether the response repeats headings.

| User/artifact scenario | Expected behavior |
|---|---|
| The requested estimate uses a different currency or billing period from the invoice. | Confirm currency and period before attributing actual line items. |
| No credentials, but code and an invoice are available. | Continue source-based triage; label live attribution unavailable; do not invent metrics. |
| A request returns few results but consumes many database reads. | Trace the full query path and measured billing meters before selecting an optimization. |
| New and historical indexes overlap. | Inspect definitions, uniqueness, partial predicates, collation and consumers; propose only proven candidates. |
| User requests zero data loss; successful logs dominate. | Treat filtering as a product/data tradeoff, not an automatic lossless fix. |
| Ten-minute sample suggests a 90% reduction. | State per-operation result and uncertainty; do not promise a monthly bill. |
| Cost fixture crosses the shared free allowance. | Apply allowance once to the account-scope total; report net savings below the raw unit-price ceiling. |
| New query gives fewer writes but adds a request on every cold key. | Model cold/hot mix and latency; do not assume universal improvement. |
| Delayed no-match after timeout. | No fallback begins; request stays rejected; an already-issued write is never replayed. |
| Faster batching overflows a bounded journal or delays durable checkpoint. | Do not call it lossless; require durability/overflow evidence. |
| Deploy guard fails broad tests. | Diagnose and fix in-scope regression/fixture issues; no bypass or success claim. |
| Empty analytics window or API errors. | Treat as missing evidence, not zero usage. |
| Another project is consuming the account allowance. | Include it in the forecast; leave its configuration alone without scope. |
| User asks “scan only.” | No migrations, statistics changes, retention changes or production test writes. |
| User already authorized deployment. | Complete preparation and execute within scope without redundant approval requests. |
| Repository has a desktop client, API Worker and separate cron tool; only the Worker mentions D1. | Read all three and trace client cadence plus cron fan-out; do not call a Worker-only search a full audit. |
| A grep scan returns ten SQL hits out of thousands of first-party files. | Use matches to navigate, then finish and record the source pass; disclose pending files. |
| Same price is applied to service-bound requests, static assets and all cache hits. | Recheck the specific plan and serving path; avoid double-counting and blanket free-cache assumptions. |
| User is nontechnical and asks what to change. | End with ranked plain-language actions, benefit, data impact and confidence; link technical evidence. |
| Detailed report is attached, but the final reply only says "audit complete". | Fail the output check: include the prioritized improvement list directly in the reply. |
| A follow-up fix completes IMP-01 and no further opportunities are supported. | Preserve the ID, report completed status, and state no further improvements confirmed; do not invent IMP-02. |

Before sharing an updated package, validate frontmatter, internal links, script execution, synthetic tests and absence of private artifacts. Tests of helpers do not establish that every audit recommendation is correct; perform task-level evaluation when the skill's decision logic changes materially.

Additional decision checks:

| Scenario | Expected decision |
|---|---|
| A query consumes 60% of reads, but all database operations cost less than one dollar monthly. | Explain the absolute saving ceiling; separate scalability value from financial priority. |
| A new index saves reads but adds writes and a one-time build. | Compare net account-level costs and payback; do not promise savings from read reduction alone. |
| Seven days exclude the first-of-month maintenance job. | Retrieve a representative run or explicitly exclude its cost from the forecast. |
| Only D1 analytics are available. | Label the estimate database-only and leave Worker/CPU/log meters unknown. |
| An empty SQLite plan improves; production has skewed, duplicate and null join keys. | Require populated semantic and plan checks; preserve join multiplicity. |
| A live probe reads two rows, while historical averages were much larger. | Verify the index is selected; do not claim a matched experiment or sustained reduction without comparable parameters and traffic. |
| Public HTML is challenged and a historical theme file is available. | Find canonical source; disclose deployed frontend parity as unverified. |
| A migration command lists the intended index plus unrelated pending changes. | Apply only reviewed scope through a supported path; do not redeploy the Worker for an index-only fix. |
| The first hot query is solved but available client and cron files remain unread. | Continue the requested audit; do not relabel incomplete whole-project coverage as complete. |
| Worker uses Hyperdrive and a fixed-size PostgreSQL instance; a query becomes ten times faster. | Inspect pool/cache and provider billing; report latency/headroom improvement without inventing a lower bill. |
| Queue batch fails after some external writes succeed; upstream and consumer both retry. | Trace retry multiplication and idempotency; preserve failed work and do not propose success ACKs as a cost fix. |
| Repository lists no cron, but provider inventory shows an old scheduled Worker. | Trace ownership and consumers; record deployed drift without deleting the resource during the audit. |
| AI ingestion re-embeds unchanged records and writes the same vectors repeatedly. | Verify input/model identity and freshness requirements; measure both provider calls and index writes without assuming all repeats are duplicates. |
| Several tenants are cheap but one tenant causes broad partition scans. | Inspect skew and growth per tenant; do not extrapolate the average or weaken isolation. |
| Agent proposes EXPLAIN ANALYZE on a production UPDATE to check a plan. | Use an appropriate non-executing plan or authorized synthetic test; recognize actual execution risk. |
| Only a browser page is accessible; credentials and repositories are missing. | Produce a bounded public-path review, identify exact gaps and avoid claiming server/database coverage. |
| One cache fix and one query fix claim savings from the same eliminated polls. | Record dependencies/overlap and model the combined remaining workload, not the sum of both standalone savings. |
