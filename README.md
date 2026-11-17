# Cloudflare GLP1
<img width="1152" height="1728" alt="image" src="https://github.com/user-attachments/assets/516175fa-c735-4dee-a38f-edba0a03672f" />

An AI agent skill that finds unnecessary Cloudflare spending, traces it to your code, and recommends practical changes without silently sacrificing data or application behavior.

Independent community skill. Not affiliated with or endorsed by Cloudflare.

## What it does

Cloudflare GLP1 reviews the paths that generate billed usage across your project:

- Workers, APIs, and their desktop, mobile, or web clients
- D1 queries, indexes, and database access patterns
- Queues, scheduled jobs, retries, and service-to-service calls
- Storage and other configured Cloudflare services

It connects source code with available usage and billing evidence, then ranks improvements by practical value and expected net savings.

When measurements are missing, it says so. It does not invent costs or savings.

## Modes

| Mode | Purpose |
|---|---|
| Scan/report | Inspect source, configuration, billing, and read-only metrics |
| Fix | Implement authorized, scoped improvements |
| Verify | Test changes and distinguish local results from production evidence |
| Deploy/observe | Follow the project's deployment controls and verify the rollout |

An audit request does not authorize production changes, migrations, data deletion, or deployment.

## Installation

Copy this repository into your agent's skills directory under `cloudflare-glp1`.

For Codex, a typical location is:

```text
~/.codex/skills/cloudflare-glp1/
```

Keep the directory structure intact:

```text
cloudflare-glp1/
├── SKILL.md
├── agents/
├── references/
├── scripts/
├── examples/
└── evals/
```

## Usage

Ask your agent to use the skill and describe the scope.

### Review a project

> Use $cloudflare-glp1 to audit this project's Cloudflare costs. Trace the billed work to its callers, rank improvements, and report coverage gaps. Do not change production.

### Investigate D1 usage

> Use $cloudflare-glp1 to investigate high D1 rows-read usage. Review queries, indexes, caller frequency, retries, and scheduled jobs. Preserve existing data and behavior.

### Verify a proposed fix

> Use $cloudflare-glp1 to verify this optimization. Compare query work and retained data, test relevant behavior, and state what remains unproven in production.

Provider credentials are optional for source-only reviews. Live collection requires explicitly configured access. Never paste credentials into prompts or commit them to this repository.

## Included tools

The Python tools use the standard library.

| Tool | Purpose |
|---|---|
| `collect_evidence.py` | Collect bounded provider evidence; dry-run by default |
| `benchmark_sqlite.py` | Compare query work and data preservation using synthetic SQLite workloads |
| `audit_models.py` | Model growth, regression thresholds, timelines, invoice attribution, and evaluation scores |
| `inspect_indexes.py` | Inspect a local SQLite database read-only for potential index overlap |
| `estimate_cost.py` | Compare scenarios for one usage meter using supplied rates |

Read [the toolkit reference](references/toolkit.md) before running tools.

Run the helper tests from the repository root:

```sh
python scripts/test_helpers.py
python scripts/test_audit_tools.py
```

## What to expect

An audit identifies:

- What was reviewed and what remains unknown
- Which operations generate unnecessary work
- The supporting source and measured evidence
- What to change first and why
- Expected savings, assumptions, and data or behavior tradeoffs
- The validation needed before deployment

## Evidence and safety

The skill requires current official documentation before assessing platform behavior. It favors bounded, aggregate evidence over customer records.

Synthetic SQLite results do not prove D1 billing savings or production concurrency behavior. A short observation window does not establish a monthly bill.

Retention reductions, sampling, caching, and delayed delivery can change application guarantees. Those tradeoffs must be explicit.

Project rules and user authorization remain authoritative.
