# 05 — 组合优化函数

> 聚宽内置的投资组合优化器，在约束条件下计算最优权重。

## portfolio_optimizer

```python
from jqlib.optimizer import *

portfolio_optimizer(
    date, securities, target, constraints,
    bounds=[Bound(0.0, 1.0)],
    default_port_weight_range=[0.0, 1.0],
    ftol=1e-9,
    return_none_if_fail=True
)
```

**参数**：
- `date`：优化发生日期，注意未来函数
- `securities`：股票代码列表
- `target`：目标函数（只能选一个，见下方）
- `constraints`：限制函数列表（可多个，见下方）
- `bounds`：边界函数列表（可多个，见下方）。默认 `[Bound(0., 1.)]`
- `default_port_weight_range`：默认权重和范围 `[0.0, 1.0]`
- `ftol`：优化精度，默认 `1e-9`。精度不够时降低，速度慢时提高
- `return_none_if_fail`：优化失败时 `True` 返回 `None`，`False` 返回全零权重

---

## 目标函数 (target)

只能选一个。

| 函数 | 说明 | 参数 |
|---|---|---|
| `MinVariance(count=250)` | 最小化组合方差 | `count`: 向前取天数 |
| `MaxProfit(count=250)` | 最大化组合收益 | `count`: 向前取天数 |
| `MaxSharpeRatio(rf=0.0, weight_sum_equal=1.0, count=250)` | 最大化夏普比率 | `rf`: 无风险利率 |
| `MinTrackingError(benchmark, count=250)` | 最小化追踪误差 | `benchmark`: 基准代码 |
| `RiskParity(count=250, risk_budget=None)` | 风险平价 | `risk_budget`: pd.Series |
| `MaxScore(scores)` | 打分最大化 | `scores`: pd.Series |
| `MinScore(scores)` | 打分最小化 | `scores`: pd.Series |
| `MaxFactorValue(factor, count=1)` | 因子值最大化 | `factor`: Factor 子类 |
| `MinFactorValue(factor, count=1)` | 因子值最小化 | `factor`: Factor 子类 |

**Factor 子类示例**（用于 `MaxFactorValue`/`MinFactorValue`）：
```python
from jqfactor import Factor

class AR(Factor):
    name = 'AR_M5'
    max_window = 5
    dependencies = ['AR']
    def calc(self, data):
        return data['AR'].mean()

target = MaxFactorValue(factor=AR, count=1)
```

---

## 限制函数 (constraints)

可设置多个。

| 函数 | 说明 |
|---|---|
| `WeightConstraint(low=0.0, high=1.0)` | 组合总权重上下限 |
| `WeightEqualConstraint(limit=1.0)` | 组合总权重等于某值 |
| `AnnualStdConstraint(limit, count=250)` | 年化标准差上限 |
| `AnnualProfitConstraint(limit, count=250)` | 年化收益率下限 |
| `IndustryConstraint(industry_code, low, high)` | 行业权重限制 |
| `IndustriesConstraint(industry_code, low, high)` | 行业分类权重限制 |
| `MarketConstraint(market_type, low, high)` | 市场类型权重限制 |
| `ExposureConstraint(factor, low, high, count)` | 因子暴露限制 |
| `BarraConstraint(size=None, beta=None, ...)` | Barra 风险因子暴露限制 |
| `IndustryDeviationConstraint(industry_code, benchmark, limit)` | 行业偏离度 |
| `IndustriesDeviationConstraint(industry_code, benchmark, limit)` | 行业分类偏离度 |
| `TrackingErrorConstraint(benchmark, limit, count)` | 追踪误差 |
| `TurnoverConstraint(limit, current_portfolio)` | 换手率 |
| `RatioConstraint(ratio, low, high, rf, benchmark, count)` | 比率限制 |
| `MaxDrawdownConstraint(limit, count)` | 最大回撤 |

**BarraConstraint 参数**（10 个风险因子，各传 `[low, high]` 列表）：
```python
constraint = BarraConstraint(
    size=[-0.5, 0.5],
    beta=[None, 1.5],
    winsorize=False
)
```

**RatioConstraint 支持的 ratio**：
`sharpe_ratio`, `information_ratio`, `calmar_ratio`, `omega_ratio`, `sortino_ratio`, `var`, `cvar`

---

## 边界函数 (bounds)

对单只标的权重限制。

| 函数 | 说明 |
|---|---|
| `Bound(low=0.0, high=1.0)` | 每只标的权重范围 |
| `IndustryBound(industry_code, low, high)` | 按行业限制单股权重 |
| `LiquidityBound(limit, capital, count, subset)` | 流动性限制 |
| `CapBound(limit, capital, count, subset)` | 市值限制 |

**多个 Bound**：股票权重下限取各 Bound 的最大值，上限取最小值。

---

## 完整示例

```python
import pandas as pd
from jqdata import *
from jqfactor import Factor
from jqlib.optimizer import *

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        min_commission=5
    ), type='stock')
    run_monthly(rebalance, monthday=1, time='09:31')

def rebalance(context):
    stocks = get_index_stocks('000300.XSHG')[:20]
    date = context.current_dt.strftime('%Y-%m-%d')

    weights = portfolio_optimizer(
        date=date,
        securities=stocks,
        target=MinVariance(count=250),
        constraints=[
            WeightEqualConstraint(limit=1.0),
            AnnualStdConstraint(limit=0.15, count=250),
        ],
        bounds=[Bound(0.0, 0.1)],
    )

    if weights is not None:
        for stock, w in weights.items():
            if w > 0:
                order_target_value(stock, context.portfolio.total_value * w)
```

---

## 常见失败模式

❌ `from jqlib import optimizer` → 正确写法 `from jqlib.optimizer import *`
❌ 传了多个 `target` → 只能选一个
❌ `date` 用了未来日期 → 未来函数
❌ 优化求解超时 → 提高 `ftol` 值或减少股票数量
❌ 所有权重为 0 → 约束条件矛盾，检查 constraints 和 bounds 是否冲突
