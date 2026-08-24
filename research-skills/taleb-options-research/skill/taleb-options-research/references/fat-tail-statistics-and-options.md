# Fat-tail statistics and options

## Purpose and source

This reference converts reviewed results from Nassim Nicholas Taleb's *Statistical Consequences of Fat Tails: Real World Preasymptotics, Epistemology, and Applications — Papers and Commentary*, Third Edition (2025), source ID `SCOFT-3E-2025`, into research checks.

It does not contain the book, OCR, figures, or a profitable-strategy claim. Query the release registries by `SCOFT-` or `RULE-SCOFT-` IDs for locators, assumptions, and limitations.

## Decision hierarchy

Apply the book's results in this order:

1. Analyze the exact payoff \(f(X)\), not only a forecast of \(X\).
2. Protect survival against absorbing loss and forced liquidation.
3. Establish finite-sample and estimator sufficiency.
4. Separate physical, pricing-implied, subjective, and stress quantities.
5. Propagate parameter, tail, dependence, and model uncertainty.
6. Test costs, margin, path, liquidity, and hedge error.
7. Compare no-trade and simple structures before complexity.

A fat-tailed driver does not prove that a quoted option is cheap. Convexity can be overpriced, path-fragile, or operationally inaccessible.

## Preasymptotic and moment checks

Asymptotic convergence is not a finite-sample certificate. Record:

- nested-sample and regime results;
- seed and block stability for simulation;
- the moment order required by each estimator;
- maximum-to-sum concentration for returns, P&L, and hedge errors;
- how performance changes when the largest observations are withheld or plausible missing extremes are injected.

Where applicable, use the source's \(\kappa\) scaling metric:

\[
\kappa(n_0,n)
=
2-\frac{\log n-\log n_0}
{\log(M(n)/M(n_0))},
\qquad
M(n)=\mathbb{E}|S_n-\mathbb{E}S_n|.
\]

Treat \(\kappa\) as an uncertain convergence diagnostic, never as an entry signal. Mark results inconclusive when tail-sensitive outputs do not stabilize over the declared range.

## Extremes and concentration

When subexponential behavior is plausible, preserve the one-big-jump scenario:

\[
\Pr(X_1+\cdots+X_n>x)
\sim
\Pr(\max_i X_i>x).
\]

This is a conditional asymptotic property. It supports jump-concentrated stress; it does not prove a market's tail class.

Never use the historical maximum as a future bound. Sweep threshold, support, truncation, tail exponent, and left/right asymmetry. A long calm interval is not proof of structural safety.

## Probability and option-surface measures

Keep separate:

- a physical frequency or severity model;
- an arbitrage-consistent pricing measure;
- a subjective forecast;
- a deliberately non-probabilistic stress.

Under the source's normalized same-maturity convention:

\[
C(K)-P(K)+K=F,
\qquad
\frac{\partial C(K)}{\partial K}=-\Pr_Q(S_T>K).
\]

Real implementations must restore discounting, carry, dividends, exercise, and settlement. Use finite differences and quantify smoothing error. The extracted quantity is pricing-implied; it is not automatically a physical probability.

Before inference, validate put-call parity, strike monotonicity, and convexity. Store both option prices and implied-volatility coordinates; an implied volatility can be a quoting coordinate without making its diffusion dynamics true.

## Conditional power-law relative pricing

For a Pareto right tail beyond \(l\), \(\alpha>1\), and strikes in the same tail region, the source gives:

\[
C(K)=\frac{K^{1-\alpha}l^\alpha}{\alpha-1},
\qquad
C(K_2)
=
\left(\frac{K_2}{K_1}\right)^{1-\alpha}C(K_1).
\]

Use these only to form an anchor-relative research envelope. Required gates:

- defensible tail threshold and finite-first-moment condition;
- separate \(\alpha\), threshold, truncation, and anchor sweeps;
- no circular use of the same quotes for calibration and validation;
- executable bid/ask, depth, carry, settlement, and cost checks;
- holdout and multiple-testing controls.

An observed deviation can indicate data error, liquidity, model error, or a research candidate. It is not itself arbitrage or execution authority.

## Discrete hedge error and joint dependence

Dynamic hedging does not make jump exposure disappear. Simulate the actual rebalance frequency with spreads, slippage, funding, partial fills, quote outages, gaps, margin, and no-rebalance branches. Attribute total hedge error to the worst intervals.

For multi-asset portfolios, do not grant survival-critical diversification from historical linear correlation alone. Stress co-jumps, nonlinear tail dependence, volatility and skew shifts, regime changes, and simultaneous liquidity withdrawal.

## Tail-constrained barbell

Define a real catastrophic-loss envelope first. Then describe:

- the unit and account that must survive;
- the robust reserve instrument and impairment scenarios;
- the bounded risk budget for the convex sleeve;
- the insured portfolio and numeraire;
- premium bleed, replenishment, rebalance, and expiry policy;
- account-transfer and margin constraints;
- no-trade, cash-only, underlying-only, and simple-option baselines.

Maximum-entropy reasoning may preserve uncertainty outside the hard constraints, but the chosen constraints determine the construction. The source does not provide a universal reserve/option ratio or a structure that profits in every state.

## StrategySpec block

`fat_tail_robustness` is optional for backward compatibility. Include it whenever a candidate relies on tail inference, convexity, dynamic hedging, joint diversification, or a barbell claim. It records:

- `preasymptotic_tests`
- `moment_requirements`
- `extreme_scenarios`
- `parameter_uncertainty`
- `probability_measure_labels`
- `joint_tail_tests`
- `hedge_error_tests`
- `selection_controls`
- `tail_constraint`

Schema validation confirms structure only. It does not establish data readiness, simulation success, paper-watch approval, or permission to trade.
