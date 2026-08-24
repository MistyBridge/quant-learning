---
name: taleb-options-research
description: Evidence-governed options research and strategy audit using Taleb and Xu Zhe principles. Use when analyzing, designing, screening, comparing, or challenging barbell, two-tail, calendar, dynamic-roll, compound-option, antifragile, net-credit, vega-neutral, or crash-profit claims, and when converting them into falsifiable StrategySpecs with survival, price, path, execution, benchmark, and no-trade gates.
---

# Taleb Options Research

Treat this Skill as a research and audit workflow, not a signal service. Never promise profit, infer a user's risk budget, connect an account, request credentials, or place an order.

## Route the task

Classify the request before analyzing it:

1. `SOURCE_RESEARCH`: explain or verify what a source supports.
2. `STRATEGY_DESIGN`: turn an idea into a falsifiable StrategySpec.
3. `STRATEGY_AUDIT`: challenge a claim, payoff, backtest, or proposed trade.
4. `SCREENING_SPEC`: define data fields and gates for a future scanner.
5. `RESULT_REVIEW`: evaluate research, simulation, or paper-watch output.

Do not force this framework onto a request that only mentions an ordinary option term.

## Select the evidence mode

Use `PUBLIC_CORE` by default. Read the release registries and source manifest. State that locators have not been checked against original pages in the current session.

Use `BYOS_VERIFIED` only when the user explicitly supplies legally obtained local sources and the local index passes the verification scripts. Never search the user's home directory for books.

If a critical record is unknown, withheld, edition-mismatched, or contradicted, keep it `U` and identify the required re-check. Do not reconstruct missing quotations.

## Load only the references needed

- Read [core-method.md](references/core-method.md) for survival, convexity, price, path, measure, and benchmark gates.
- Read [strategy-families.md](references/strategy-families.md) when routing F1–F4, B1–B5, or F5.
- Read [evidence-and-parameter-governance.md](references/evidence-and-parameter-governance.md) for evidence levels, parameter status, release records, and BYOS rules.
- Read [validation-and-output-contract.md](references/validation-and-output-contract.md) when creating a StrategySpec, test plan, ranking, or audit report.
- Read [source-map.md](references/source-map.md) and [source-manifest.json](references/source-manifest.json) for source IDs and locator conventions.
- Read [licensing-and-sources.md](references/licensing-and-sources.md) before quoting, packaging, or sharing evidence.
- Read [fat-tail-statistics-and-options.md](references/fat-tail-statistics-and-options.md) when a task depends on preasymptotics, moment sufficiency, extreme-value extrapolation, power-law relative pricing, discrete hedge error, joint-tail dependence, or a tail-constrained barbell.
- Query the release JSONL files by stable ID; do not load every registry when a narrow lookup is enough.

## Apply the research sequence

1. State the task, market scope, evidence mode, valuation time, and account/numeraire boundary.
2. Resolve canonical contract identity for every leg:
   - underlying and contract multiplier;
   - put/call or exotic payoff;
   - side and integer quantity;
   - strike, expiry, exercise style, settlement, currency;
   - listed, OTC, dynamic replica, or research-synthetic status.
3. Separate every input into:
   - `CONTRACT`
   - `LITERATURE`
   - `CALIBRATE`
   - `USER_POLICY`
   - `STRESS`
   - `MISSING_FROM_SOURCE`
   - `UNKNOWN`
4. Compute pathwise per-account liquidation wealth and survival before ranking return.
5. Apply fat-tail robustness where material: test preasymptotic convergence, required moments, extreme concentration, parameter uncertainty, probability-measure labels, and joint-tail/hedge-error scenarios.
6. Evaluate net convexity after premium, carry, financing, spread, depth, fees, hedge, assignment, margin, partial fill, and liquidation cost.
7. Revalue across spot × time × volatility surface × liquidity/margin states. Do not substitute a terminal payoff chart for the path.
8. Compare in this order:
   - `F5_NO_TRADE`
   - B1–B5 simple baselines
   - F1–F4 complex candidates
9. Reject or keep in research when required contracts, executable quotes, permissions, settlement, margin, or data history are unavailable.
10. Report the conclusion conditionally with the largest known risk, unknowns, and falsification conditions.

## Enforce the hard gates

Reject, downgrade, or return `NO_TRADE` when any gate fails:

- `SURVIVAL`: a registered stress path breaches the user-supplied liquidation floor.
- `PRICE`: optionality or convexity is asserted without premium and total-cost comparison.
- `CONTRACT`: a leg, payoff, exercise, settlement, or numeraire is ambiguous.
- `DATA`: point-in-time chains, executable quotes, or required state history are missing.
- `PATH`: only expiry payoff or two hand-picked stress points are shown.
- `COST`: spread, depth, partial fill, funding, hedge, assignment, or liquidation is omitted.
- `MARGIN`: account-level margin and forced-unwind behavior are not modeled.
- `SELECTION`: the search universe, rejected variants, or multiple testing is hidden.
- `PREASYMPTOTIC`: the required estimator or simulation does not stabilize over the declared sample, block, seed, or aggregation ranges.
- `MEASURE`: physical, pricing-implied, subjective, and stress quantities are conflated.
- `DEPENDENCE`: survival-critical diversification relies only on historical linear correlation.
- `BENCHMARK`: the candidate is not compared with no-trade and simple structures.
- `COMMUNICATION`: language implies guaranteed, no-loss, or unconditional antifragility.

Treat `NO_TRADE` as a valid result, not as an analysis failure.

## Route strategy families

Use these stable identities:

- `F1_SAME_EXPIRY_WINGS`
- `F2_CROSS_EXPIRY_WINGS`
- `F3_DYNAMIC_HARVEST_REBUILD`
- `F4_DIRECT_COMPOUND`
- `B1_LONG_PUT`
- `B2_LONG_CALL`
- `B3_LONG_TWO_TAILS`
- `B4_PROTECTIVE_PUT`
- `B5_SHORT_STRADDLE`
- `F5_NO_TRADE`

Never convert source examples such as 90/10, 60/20/80, a moneyness, an expiry, or a stress point into a production default.

Preserve the E43 replacement-put buy/sell conflict as `UNKNOWN`. Model alternative branches if useful; do not choose a side by interpretation.

## Validate machine artifacts

Validate a single or portfolio StrategySpec:

```text
python scripts/validate_strategy_spec.py <artifact.json> --mode single
python scripts/validate_strategy_spec.py <artifact.json> --mode portfolio
```

Validate release evidence:

```text
python scripts/validate_release_evidence.py
```

Index explicit local sources and create a local review cache:

```text
python scripts/index_local_sources.py SOURCE_ID=PATH --output local-index.json
python scripts/verify_source_manifest.py local-index.json
python scripts/build_local_evidence_cache.py local-index.json --evidence-root <path>
```

Keep the evidence root outside this Skill. These scripts are offline and must not upload or download source content.

## Produce the result

Use the output contract in [validation-and-output-contract.md](references/validation-and-output-contract.md). At minimum include:

- decision state and research-only notice;
- evidence mode and source IDs/locators;
- canonical legs and unresolved identities;
- parameter registry with statuses;
- survival, cost, path, margin, and selection findings;
- comparison with F5 and simple baselines;
- known unknowns and falsification conditions;
- data required for the next authorized research phase.

Do not call a candidate executable merely because its schema validates. Schema validity is not market-data readiness, simulation success, paper-watch approval, or execution authority.
