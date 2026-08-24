![Taleb Options Research — Evidence, Convexity, Survival](assets/taleb-options-research-header.png)

# Taleb Options Research

[中文](README.zh-CN.md) | English

This Codex Skill turns options ideas inspired by Xu Zhe and Nassim Nicholas
Taleb into research that can be checked and disproved. It is useful when you
want to examine a contract, compare structures, write precise rolling rules, or
find out what data a strategy still needs.

The Skill is a research method, not a trading signal. Its conclusion may be
that a candidate deserves further testing, that the evidence is incomplete, or
that the appropriate decision is `NO_TRADE`.

Current release: **1.1.0**

## What can it do?

| What you want to do | What you provide | What the Skill returns | Market-data requirement |
|---|---|---|---|
| Check what Xu Zhe, Taleb, or a reviewed source actually supports | A question, claim, or source scope | A source-backed explanation with locators, limitations, conflicts, and unresolved points | None |
| Analyze one option contract | Contract identity, quote time, bid/ask, contract terms, and relevant account constraints | Contract checks; expiry payoff; path, price, liquidity, margin, exercise, and assignment findings; a conditional decision | You supply a current snapshot |
| Compare a multi-leg structure with simpler alternatives | Every leg, executable quotes, proposed quantities, and a risk or premium budget | Side-by-side payoff and path analysis, total-cost comparison, hidden loss regions, hard rejects, and `NO_TRADE` | You supply a synchronized snapshot |
| Turn an idea into a testable strategy | The thesis, market scope, available instruments, constraints, and intended holding or rolling logic | Explicit legs, parameters, entry/rebalance/exit rules, data requirements, benchmarks, risk limits, and falsification tests | Not needed for the initial design; needed before market testing |
| Formalize a roll or harvest rule | Current position, observation schedule, triggers, branch actions, stop conditions, and cost assumptions | A state machine, complete cash ledger, ambiguous branches, failure conditions, and required data | Depends on the rule; historical and point-in-time data are usually needed for testing |
| Screen a chain that you supply | A point-in-time option chain with executable prices and contract details, plus liquidity and risk constraints | Eligible and rejected contracts, a conditional ranking, reasons for each result, and possibly `NO_TRADE` | You supply the chain; the Skill does not fetch it |
| Review a backtest, simulation, candidate list, or paper-trading report | Results, methodology, data scope, cost assumptions, and preferably the full search log | An audit of selection bias, unstable estimates, dependence on extreme days, missing costs, margin paths, and benchmark integrity | No live feed; the underlying test data must be available |
| Specify a future US or crypto option scanner | Intended universe, venues, account constraints, and research objective | Required fields, filters, ranking rules, rejection gates, snapshots, and output schema | No; this designs the scanner but does not run one |

### Can it help select options?

Yes, but the answer depends on the data available:

| Available data | What the Skill can do |
|---|---|
| No market data | Explain the source material, define a structure, derive its payoff, and specify tests. It cannot decide whether current contracts are attractively priced or executable. |
| A chain or quote snapshot supplied by you | Analyze and rank only the contracts in that snapshot, subject to the declared constraints. A valid result may still be `NO_TRADE`. |
| Live chains, history, and a data connector | Repeated full-universe monitoring would become possible, but those connectors and the scanner are **not included in this release**. |

The Skill can therefore suggest **research candidates** and compare them under
stated assumptions. It does not autonomously choose the best live option, issue
a personalized trade instruction, or submit an order.

## What does an analysis contain?

The depth depends on the question and the data, but a complete result normally
covers:

| Part of the result | What it answers |
|---|---|
| Conclusion | What passed, what failed, the current decision state, and the largest known risk |
| Contract definition | Exact legs, sides, quantities, strikes, expiries, multiplier, exercise, settlement, currency, and unresolved fields |
| Payoff and path | Expiry payoff, shoulder-loss regions, and mark-to-market behavior across spot, time, volatility surface, and liquidity/margin states |
| Price and survival | Premium, carry, spread, depth, fees, funding, assignment, margin, partial fills, forced unwind, and account liquidation risk |
| Comparison | The same idea measured against a simpler option structure and `NO_TRADE` under a declared budget |
| Evidence | Source IDs, locators, formulas, derivations, and the distinction between source facts, calibrated values, stress assumptions, and unknowns |
| Next test | Missing data, falsification conditions, and what would permit or reject the next research stage |

When requested, the result can also be written as a machine-validatable
**StrategySpec**. Schema validity means that the research contract is internally
well formed; it does not mean that the strategy has passed simulation or is
ready to trade.

## Examples

After installation, mention `$taleb-options-research` in an ordinary request.
For example:

- Analyze this SPY put using the attached quote and contract details. Show the
  premium at risk, path risks before expiry, liquidity concerns, and the
  conditions that would reject it.
- Compare this long strangle, the proposed four-leg wing structure, and doing
  nothing under the same premium budget.
- Check whether this “profits in both tails” claim hides losses in the shoulder
  regions or depends on an unrealistic fill.
- Turn these rolling notes into explicit states, triggers, cash movements, and
  stop conditions.
- Review this backtest. Most of its return comes from three extreme days; check
  estimator stability, costs, and whether the search process leaked into the
  holdout.
- Define the fields and rejection rules required for a scanner covering US
  equity options or crypto options.

The more precise the contract identity, quote time, executable prices, account
constraints, and research objective, the more specific the result can be.

## What it does not do yet

- Fetch live option chains or historical market data.
- Monitor all listed US or crypto options on a schedule.
- Connect Schwab, IBKR, OKX, Binance, or another broker or exchange.
- Run a credible backtest without the necessary data and an external research
  environment.
- Place real or simulated orders, request account credentials, or manage a
  portfolio.
- Guarantee profit or turn a source example into a production parameter.

Live monitoring, brokerage/exchange integration, backtesting, and paper trading
belong to the later `evidence-based-options-strategy-v1` platform project. This
release supplies the research logic and output contracts that such a platform
can use.

## How the method evaluates an idea

1. **Define the contract.** Every leg must have an unambiguous side, quantity,
   strike, expiry, exercise style, settlement, multiplier, and currency.
2. **Check survival before return.** Account liquidation, margin expansion,
   gaps, assignment, and forced unwind are evaluated before ranking expected
   return.
3. **Revalue the path.** A terminal payoff chart is not enough. The position is
   examined across spot, time, volatility-surface, liquidity, and margin states.
4. **Count the whole cost.** Premium, carry, financing, spread, depth, fees,
   hedge cost, partial fills, and liquidation all belong in the comparison.
5. **Use honest baselines.** A complex structure must beat an appropriate
   simple alternative and `NO_TRADE` under the same stated budget.
6. **Try to disprove the claim.** The result records unknowns, missing data,
   stress cases, holdout requirements, and conditions that would reject the
   thesis.

For tail-dependent work, the Skill also checks whether the available sample can
support the statistic being used, whether a few extremes dominate the result,
whether probability measures have been mixed, and what happens beyond the
historical maximum.

## Strategy structures covered

| Research family | What is examined |
|---|---|
| Same-expiry wings (`F1`) | Long outer put/call wings with short central optionality, including both shoulder-loss regions and short-gamma margin |
| Cross-expiry wings (`F2`) | Calendar or diagonal structures, including forward volatility, skew, residual long-option life, and executable rolls |
| Dynamic harvest and rebuild (`F3`) | Versioned rolling policies with triggers, branch actions, cash ledgers, stale quotes, and stop states |
| Direct or replicated compound optionality (`F4`) | Listed, OTC, dynamically replicated, or research-synthetic “option on an option” claims, kept as distinct instrument types |
| Simple baselines (`B1`–`B5`) | Long put, long call, long two tails, protective put, and a short-volatility counterexample |
| No trade (`F5`) | Avoided cost and risk, opportunity cost, missing data, and the condition that would reopen research |

Examples from books or discussions—such as allocation ratios, moneyness, expiry,
or stress points—remain research references. The Skill does not silently turn
them into default trade settings.

## Installation

Clone the repository, then copy the installable Skill into your Codex skills
directory.

macOS/Linux:

```bash
git clone https://github.com/trigeek/taleb-options-research-skill.git
cp -R taleb-options-research-skill/skill/taleb-options-research ~/.codex/skills/
```

Windows PowerShell:

```powershell
git clone https://github.com/trigeek/taleb-options-research-skill.git
Copy-Item -Recurse .\taleb-options-research-skill\skill\taleb-options-research "$HOME\.codex\skills\"
```

Restart or refresh Codex skill discovery after installation. The installable
directory is [`skill/taleb-options-research`](skill/taleb-options-research/);
the repository READMEs are not part of the runtime Skill.

## StrategySpec validation

Validate one research record:

```bash
python skill/taleb-options-research/scripts/validate_strategy_spec.py artifact.json --mode single
```

The validator requires the Python `jsonschema` package. Portfolio validation is
also supported with `--mode portfolio`. All bundled specifications require
`execution_authority=false`.

## Sources and evidence

The public release contains project-authored summaries and structured research
records, not copies of the source works.

| Level | Meaning |
|---|---|
| `D` | Direct source record with a locator |
| `B` | Source-supported interpretation |
| `C` | Cross-source synthesis |
| `A` | Independent derivation or recomputation |
| `U` | Unresolved, contradictory, or missing |

The release records known conflicts instead of guessing. For example, the
buy/sell direction of the replacement put discussed in Xu Zhe E43 remains
marked `U`.

Version 1.1.0 includes:

- 422 claim summaries, 233 formula records, 245 visual-metadata records without
  source images, and 183 research rules;
- a chapter-by-chapter review of Taleb's *Statistical Consequences of Fat
  Tails*, Third Edition (2025), identified as `SCOFT-3E-2025`;
- preasymptotic, moment-admissibility, extreme-concentration, one-big-jump,
  beyond-maximum, joint-tail, discrete-hedging, and multiple-testing checks;
- conditional power-law relative-pricing research and a tail-constrained
  barbell specification;
- an optional, backward-compatible `fat_tail_robustness` StrategySpec block.

See the
[public source inventory](skill/taleb-options-research/references/source-inventory.release.md)
for the reviewed source list. Original books, audio, transcripts, OCR, page
images, and private review manifests are not included.

### Public Core and your own sources

The installed Skill works in `PUBLIC_CORE` mode using the release registries.
In this mode, it discloses that the original pages were not rechecked during the
current session.

If you lawfully hold a source edition, the offline BYOS tools can index it and
build a local review cache:

```bash
python skill/taleb-options-research/scripts/index_local_sources.py \
  SCOFT-3E-2025=/path/to/your/lawful-third-edition.pdf \
  --output /path/to/local-index.json

python skill/taleb-options-research/scripts/verify_source_manifest.py \
  /path/to/local-index.json

python skill/taleb-options-research/scripts/build_local_evidence_cache.py \
  /path/to/local-index.json \
  --evidence-root /path/outside/the/repository
```

These tools are offline: they do not search the home directory, download
sources, or upload content. Local hashes, OCR, page mappings, and review notes
must remain outside both this repository and the installed Skill.

## Repository validation and release

Run:

```bash
python skill/taleb-options-research/scripts/validate_release_evidence.py
python skill/taleb-options-research/scripts/run_self_tests.py
python skill/taleb-options-research/scripts/package_public_skill.py --output dist
```

The self-tests require `jsonschema`. The packager uses an explicit allowlist,
checks for local paths and secrets, writes a manifest, and audits the extracted
archive.

The versioned installable archive is available from the
[v1.1.0 GitHub release](https://github.com/trigeek/taleb-options-research-skill/releases/tag/v1.1.0).

## Licensing

- Code, scripts, and JSON Schema: [Apache License 2.0](LICENSE).
- Original documentation and project-authored release summaries:
  [CC BY 4.0](LICENSE-DOCS).
- Third-party source works are excluded, not bundled, and not relicensed. See
  [NOTICE](NOTICE).

Source titles, authors, IDs, and locators are provided for attribution and
research verification only.
