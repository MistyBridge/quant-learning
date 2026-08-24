# Strategy families

## Contents

1. Common contract
2. F1 same-expiry wings
3. F2 cross-expiry wings
4. F3 dynamic harvest/rebuild
5. F4 direct compound
6. Baselines B1–B5
7. F5 no-trade

## 1. Common contract

For every family, define canonical legs, signed quantities, contract identity, entry/exit cash flows, exercise/settlement, path states, margin, data requirements, parameter status, benchmarks, hard rejects, and falsification tests.

Use executable bid/ask/depth or atomic-combo observations. Midpoint values may diagnose a model but cannot establish tradable performance.

When a family relies on tail inference, dynamic hedging, diversification, or a barbell claim, include the optional `fat_tail_robustness` block and apply the checks in [fat-tail-statistics-and-options.md](fat-tail-statistics-and-options.md). This does not change the stable F1–F5 identities.

## 2. F1 same-expiry wings

Stable ID: `F1_SAME_EXPIRY_WINGS`.

Canonical research form:

- buy \(q_p\) OTM puts at \(K_p\);
- sell \(q_s\) ATM puts and \(q_s\) ATM calls at \(K_a\);
- buy \(q_c\) OTM calls at \(K_c\);
- use one expiry \(T\), with \(K_p<K_a<K_c\).

Ignoring exercise and costs, the expiry payoff is:

\[
\Pi_T(S)=q_p(K_p-S)^+
-q_s(K_a-S)^+
-q_s(S-K_a)^+
+q_c(S-K_c)^+
+C_T.
\]

For upward slopes in both far tails, require \(q_p>q_s\) and \(q_c>q_s\). This does not remove the two shoulder-loss regions. Compute their minima after financing, fees, assignment, and liquidation.

Hard rejects:

- a missing leg or mismatched expiry/settlement;
- quantity conditions asserted without integer-contract feasibility;
- shoulder loss beyond the user budget;
- short-gamma margin failure;
- a “both tails profit” label based on two endpoints;
- costs or legging risk dominate the baseline.

Compare with B3 and F5.

## 3. F2 cross-expiry wings

Stable ID: `F2_CROSS_EXPIRY_WINGS`.

Treat any “60/20/80” or modified-vega example as literature context, never as a default. A valid specification must state option type, side, strike, expiry, quantity, roll/exit time, settlement, and whether the metric is standard vega, modified vega, or a full surface sensitivity.

Required evaluation:

- full repricing at the short-leg expiry and later times;
- forward-volatility and term-structure changes;
- spot × time × skew × vol-of-vol grid;
- residual long-option lifecycle after short expiry;
- executable close/roll and margin.

Hard rejects:

- put/call, strike, or side is missing;
- initial vega neutrality is treated as path neutrality;
- a calendar payoff is evaluated only at final expiry;
- an example ratio is promoted to a calibrated weight.

Compare with B1–B3 and F5 under the same premium and survival budget.

## 4. F3 dynamic harvest/rebuild

Stable ID: `F3_DYNAMIC_HARVEST_REBUILD`.

Represent the idea as a versioned policy, not as one listed compound contract:

```text
ENTRY → MONITOR → TRIGGER → HARVEST → REBUILD → STOP
```

Specify trigger evidence, observation frequency, stale-quote handling, branch actions, integer quantities, execution order, stop time, and cash ledger.

Preserve the E43 replacement-put direction conflict:

- branch A buys a farther-OTM replacement put;
- branch B sells a farther-OTM replacement put;
- both remain research branches until the source is manually resolved;
- neither may become a default order.

Reconcile:

\[
C_{n+1}=C_n-\sum_i\Delta q_{i,n}P^{exec}_{i,n}-\text{cost}_n.
\]

Hard rejects:

- ambiguous buy/sell action hidden by prose;
- no stop time or no-cash state;
- “free option” or “negative cost” without the entire cash ledger;
- trigger depends on data unavailable at decision time;
- margin or gap risk is omitted.

Compare with static B1/B3 and F5.

## 5. F4 direct compound

Stable ID: `F4_DIRECT_COMPOUND`.

Keep four identities distinct:

1. listed compound option;
2. documented OTC compound option;
3. dynamic replica of an outer option on an inner option;
4. risk-synthetic behavior that resembles higher-order optionality.

For an outer call on an inner claim:

\[
\Pi_{T_1}=\max(V_{inner}(T_1)-K_{outer},0).
\]

Specify inner contract, outer exercise, nested settlement, counterparty/venue, valuation kernel, vol-of-vol and correlation assumptions, hedge set, and unwind.

Hard rejects:

- the instrument is not actually available;
- a dynamic replica is described as a listed claim;
- nested settlement or exercise is unresolved;
- model complexity lacks holdout or hedge-cost value;
- OTC counterparty and documentation risks are omitted.

Compare with the nearest vanilla/dynamic baseline and F5.

## 6. Baselines B1–B5

- `B1_LONG_PUT`: explicit left-tail protection; include premium bleed and skew.
- `B2_LONG_CALL`: explicit right-tail convexity; include premium bleed.
- `B3_LONG_TWO_TAILS`: long straddle/strangle-style two-sided optionality; include total premium and path-dependent monetization.
- `B4_PROTECTIVE_PUT`: underlying plus put; include basis, dividends, borrow, and account capital.
- `B5_SHORT_STRADDLE`: short straddle/strangle-style negative-convexity counterexample; include jump, margin spiral, assignment, and repeated-ruin tests.

Match candidates and baselines by declared premium, loss, margin, or survival budget. State which matching rule is used.

## 7. F5 no-trade

Stable ID: `F5_NO_TRADE`.

Record:

- avoided premium/carry/cost;
- avoided margin and model risk;
- opportunity cost under registered scenarios;
- missing data or permissions;
- the condition that would reopen research.

No-trade is mandatory when the evidence, contract, data, execution, survival, benchmark, or communication gate fails.
