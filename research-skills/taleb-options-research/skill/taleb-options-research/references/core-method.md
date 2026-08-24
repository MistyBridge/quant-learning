# Core method

## Contents

1. Objective hierarchy
2. Survival and liquidation wealth
3. Net convexity and price
4. Path and execution
5. Probability measures
6. Complexity and selection
7. Barbell and no-trade
8. Fat-tail robustness

## 1. Objective hierarchy

Apply objectives lexicographically:

1. Preserve per-account survival under declared stresses.
2. Preserve the intended exposure after premium and all execution costs.
3. Beat `NO_TRADE` and simple baselines on frozen out-of-sample tests.
4. Only then compare expected return or headline tail payoff.

This is exposure engineering, not a directional forecast. A fat-tailed world does not by itself prove that a quoted tail option is cheap.

## 2. Survival and liquidation wealth

For account \(a\), path \(\omega\), and time \(t\), use a liquidation quantity rather than a model-only mark:

\[
W^{liq}_{a,t}(\omega)
= C_{a,t}
+ \sum_i q_i P^{exit}_{i,t}(\omega)
- F_{a,t}
- H_{a,t}
- A_{a,t}
- L_{a,t},
\]

where \(C\) is cash, \(P^{exit}\) is side-and-size-aware exit value, \(F\) is financing and fees, \(H\) is hedge cost, \(A\) is exercise/assignment cash flow, and \(L\) is forced-liquidation cost.

Require a user-supplied floor:

\[
\min_{t,\omega \in \Omega_{stress}} W^{liq}_{a,t}(\omega) \ge W^{min}_a.
\]

Do not invent \(W^{min}_a\). Reject a strategy that survives only after netting capital across legally or operationally separate accounts.

Repeated exposure matters. A small per-period ruin probability can compound:

\[
P(\text{survive } n)=(1-p)^n
\]

only under the stated independence and constant-\(p\) assumptions. Use simulation or bounds when those assumptions fail.

## 3. Net convexity and price

Distinguish:

- gross payoff curvature;
- marked position curvature;
- executable liquidation curvature;
- portfolio/account curvature after costs and constraints.

On a state grid, a finite-difference probe is:

\[
\Gamma^{net}_{h}(x)
= \frac{V^{liq}(x+h)-2V^{liq}(x)+V^{liq}(x-h)}{h^2}.
\]

Positive local curvature does not prove global convexity, positive expected return, or survival. Vary \(h\), time, volatility surface, liquidity, and margin states.

Evaluate optionality together with its price:

\[
\text{incremental value}
= \text{benefit versus baseline}
- \text{premium}
- \text{carry}
- \text{implementation cost}
- \text{capital cost}.
\]

Do not use an entry credit as proof of a non-negative future payoff. Do not use a zero-debit label as proof of zero risk.

## 4. Path and execution

Terminal payoff is one projection. Preserve:

- mark-to-market paths;
- margin calls and forced unwind;
- early exercise, assignment, pin, settlement, and corporate-action branches;
- partial fills and legging risk;
- time-varying skew, term structure, vol-of-vol, rates, dividends, borrow, and liquidity;
- dynamic-policy triggers, observation frequency, stop time, and cash ledger.

For a signed position vector \(q\), record a rebalance cash account:

\[
C_{n+1}=C_n-\sum_i \Delta q_{i,n}P^{exec}_{i,n}-\text{cost}_{n}.
\]

Every dynamic replication claim must reconcile this ledger. “Self-financing” is a testable accounting condition, not a narrative label.

## 5. Probability measures

Keep four columns separate:

- `P`: empirical or physical distribution used for frequency and realized risk.
- `Q`: pricing measure used for arbitrage-consistent valuation.
- `SUBJECTIVE`: explicitly declared belief.
- `STRESS`: deliberately non-probabilistic scenario.

Never infer a physical event probability directly from a risk-neutral digital price without assumptions. Never mix a stress point into an estimated probability distribution.

## 6. Complexity and selection

Require a complete experiment ledger:

- search universe;
- variants attempted;
- data versions;
- rejected and null variants;
- selection rule;
- frozen holdout;
- costs and capacity;
- versioned policy.

A more complex surface, stochastic process, compound claim, or dynamic rule must demonstrate incremental value outside the sample that selected it. If it does not, choose the simpler baseline or no-trade.

## 7. Barbell and no-trade

A barbell separates a protected survival budget from a bounded risk budget. It is not a universal 90/10 allocation.

Define:

- the unit that must survive;
- the loss floor and horizon;
- the risky budget;
- rebalance and replenishment rules;
- cross-account transfer constraints.

Use `F5_NO_TRADE` when no candidate survives, executable data is unavailable, optionality is overpriced versus baselines, or complexity has no validated increment.

## 8. Fat-tail robustness

Do not infer finite-sample reliability from an asymptotic theorem. For every estimator, backtest, or simulation used in approval:

- declare the moment order it requires;
- measure whether maxima dominate sums and P&L;
- repeat across nested samples, blocks, seeds, thresholds, and regimes;
- include one-big-jump, clustered-extreme, and beyond-history paths;
- propagate uncertainty in volatility, jump, dependence, and tail parameters;
- label physical, pricing-implied, subjective, and stress quantities separately;
- remove survival-critical diversification credit that exists only in a historical correlation matrix.

For a strategy that claims barbell or tail protection, specify a catastrophic-loss envelope before optimizing return. Keep the robust reserve, convex sleeve, insured portfolio, numeraire, and replenishment rule explicit. There is no universal allocation and no source-supported guarantee of profit.

Use the conditional power-law call relationships in the release formulas only as an anchor-relative research diagnostic. Require a defensible common tail region, \(\alpha>1\), parameter and anchor sweeps, independent quote-quality checks, and costs. A deviation is not an executable mispricing claim.
