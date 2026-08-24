# Validation and output contract

## Contents

1. Decision states
2. Evaluation order
3. StrategySpec requirements
4. Output template
5. Falsification tests

## 1. Decision states

Use only:

- `RESEARCH`
- `SPEC_VALID`
- `DATA_READY`
- `SIM_PASS`
- `HOLDOUT_PASS`
- `PAPER_WATCH`
- `REJECT`
- `NO_TRADE`

`SPEC_VALID` means the research contract is internally valid. It does not authorize trading. This Skill always requires `execution_authority=false`.

## 2. Evaluation order

1. Canonical contract and settlement.
2. Parameter/evidence status.
3. Per-account survival and liquidation.
4. Premium, carry, execution, margin, and capacity.
5. Pathwise spot/time/surface/liquidity states.
6. No-trade and simple baselines.
7. Selection and holdout integrity.
8. Conditional conclusion and communication audit.

## 3. StrategySpec requirements

A StrategySpec must contain:

- stable `spec_id`, class, family, thesis, market scope;
- evidence/formula references;
- premium/cash-flow and risk-surface models;
- canonical legs;
- parameter registry;
- contract, settlement, path, entry, rebalance, and exit states;
- data requirements and profile IDs;
- risk limits, tests, metrics, benchmarks, hard rejects, and unknowns;
- allowed decision states.

Portfolio mode requires exactly four candidates, five baselines, and one no-trade record. Single mode requires exactly one record.

Validate JSON syntax and schema before semantic checks. Then validate:

- unique spec IDs;
- profile references;
- benchmark references;
- parameter-status consistency;
- `MISSING_FROM_SOURCE`/`UNKNOWN` values;
- F1/F2/F3/F4/F5 identity-specific invariants;
- no execution authority.

## 4. Output template

```text
Decision state:
Research-only notice:
Task and market scope:
Evidence mode:

Claim being evaluated:
What the evidence supports:
What the evidence does not support:
Source IDs and locators:

Canonical legs / unresolved identities:
Parameter registry:
Survival and liquidation:
Price, carry, and execution:
Path and margin:
Selection and holdout:

F5 no-trade comparison:
Simple baseline comparison:
Conditional conclusion:
Largest known risk:
Known unknowns:
Falsification conditions:
Next authorized research data:
```

Avoid verdicts such as “will profit,” “cannot lose,” or “is antifragile.” Prefer “passes the registered tests under these assumptions” or “remains unverified.”

## 5. Falsification tests

At minimum register:

- continuous expiry payoff grid, including shoulders;
- spot × time × surface mark-to-market grid;
- jump/gap, liquidity, spread, partial-fill, and margin stress;
- early exercise, assignment, pin, settlement, and corporate-action branches;
- full dynamic-policy cash ledger;
- simple baseline and no-trade comparison;
- frozen holdout and complete search ledger;
- parameter and model perturbation;
- nested-sample, block, seed, threshold, and regime stability;
- moment-admissibility and maximum-to-sum concentration;
- one-big-jump, clustered-extreme, and beyond-historical-maximum scenarios;
- separate physical, pricing-implied, subjective, and stress labels;
- joint-tail dependence and correlation-break scenarios;
- multiple-testing ledger for every scanned asset, strike, expiry, filter, and parameter;
- repeated-exposure and per-account survival;
- label-policy test that blocks unconditional profit claims.
