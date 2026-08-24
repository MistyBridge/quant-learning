# 07 — 对象（Order / Position / Portfolio / OrderCost / OrderStyle）

> 聚宽里 5 个最重要的对象类型。理解它们的属性，写起策略来不会卡。

## `Portfolio`（投资组合）

**访问方式**：`context.portfolio`

```python
def market_open(context):
    p = context.portfolio
    print(p.total_value)         # 总资产 = 现金 + 持仓市值
    print(p.available_cash)      # 可用现金
    print(p.locked_cash)         # 冻结资金（挂单中的金额）
    print(p.positions)           # dict[security_code, Position]
    print(p.long_positions)      # 多头持仓
    print(p.short_positions)     # 空头持仓
    print(p.starting_cash)       # 初始现金
    print(p.returns)             # 总收益率
    print(p.subportfolios)       # 子组合 list
```

**属性**：
- `total_value` — 总资产
- `available_cash` — 可用现金（**下单用**）
- `cash` — 已抵消负债的现金
- `locked_cash` — 冻结资金
- `positions` — `dict[code, Position]`，所有非空持仓
- `long_positions` / `short_positions` — 多 / 空头持仓
- `subportfolios` — `list[SubPortfolio]`，子组合
- `starting_cash` — 初始资金
- `returns` — 总收益率（小数，0.1 = 10%）
- `pnl` — 盈亏额

---

## `Position`（持仓）

**访问方式**：`context.portfolio.positions.get(security)` 或 `context.portfolio.positions[security]`

```python
pos = context.portfolio.positions.get('000001.XSHE')
if pos is not None and pos.total_amount > 0:
    print(pos.total_amount)      # 持仓数量（含 closeable + 冻结）
    print(pos.closeable_amount)  # 可平仓数量（A 股 T+1，今日买的不能卖）
    print(pos.locked_amount)     # 冻结数量（挂单中）
    print(pos.avg_cost)          # 平均成本价
    print(pos.price)             # 最新价
    print(pos.value)             # 持仓市值 = price * total_amount
    print(pos.position_value)    # 同 value
    print(pos.acc_avg_cost)      # 累计平均成本（含历史已卖出部分）
    print(pos.init_time)         # 首次建仓时间
    print(pos.transact_time)     # 上次交易时间
```

**用途速查**：
- 是否持有：`pos = context.portfolio.positions.get(s); has = pos is not None and pos.total_amount > 0`
- 浮盈率：`(pos.price - pos.avg_cost) / pos.avg_cost`
- 可卖数量：`pos.closeable_amount`（A 股 T+1，刚买的当天不能卖）

---

## `Order`（订单）

**返回方式**：所有下单函数（`order` / `order_value` / 等）的返回值

```python
o = order_value('000001.XSHE', 50000)
if o is not None:
    print(o.order_id)            # 订单 ID
    print(o.security)            # 标的
    print(o.amount)              # 委托数量
    print(o.filled)              # 已成交数量
    print(o.status)              # OrderStatus（new / open / filled / canceled / rejected / held）
    print(o.add_time)            # 委托时间
    print(o.is_buy)              # 是否买单
    print(o.price)               # 成交均价
    print(o.action)              # 操作类型
    print(o.commission)          # 手续费
```

**OrderStatus 枚举**：
- `new` — 已创建
- `open` — 已报，未成交
- `filled` — 全部成交
- `canceled` — 已撤
- `rejected` — 被拒（如资金不足）
- `held` — 部分成交，剩余挂单中

---

## `OrderCost`（交易费用）

设置费率时使用：

```python
oc = OrderCost(
    open_tax=0,                  # 买入印花税（A 股 = 0）
    close_tax=0.001,             # 卖出印花税（0.1%）
    open_commission=0.0003,      # 买入手续费（万 3）
    close_commission=0.0003,     # 卖出手续费（万 3）
    close_today_commission=0,    # 平今手续费（A 股 = 0；期货不同）
    min_commission=5,            # 最低手续费（5 元）
)
set_order_cost(oc, type='stock')
```

**type 参数**：
- `'stock'` — A 股
- `'fund'` — 基金
- `'mmf'` — 货币基金
- `'index_futures'` — 股指期货
- `'futures'` — 商品期货
- `'options'` — 期权
- `'bond_fund'` / `'stock_fund'` / 等

---

## `OrderStyle`（订单类型）

### `MarketOrderStyle()` ★

市价单。等价于 `order(s, n, style=None)`。

### `LimitOrderStyle(limit_price)` ★

限价单。

```python
order('000001.XSHE', 1000, LimitOrderStyle(15.0))
```

如果买单 limit > 当前价 → 立即按 当前价 成交  
如果买单 limit < 当前价 → 挂单，每分钟 bar 检查是否能撮合

### `MarketTPOOrderStyle()` (期货)

期货市价单。

---

## `SubPortfolioConfig`（子组合配置）

```python
set_subportfolios([
    SubPortfolioConfig(cash=500000, type='stock'),         # 第 0 个：股票，50w
    SubPortfolioConfig(cash=500000, type='index_futures'), # 第 1 个：期货，50w
])
```

下单时通过 `pindex=` 指定：
```python
order('000001.XSHE', 1000, pindex=0)
order('IF2306.CCFX', 1, pindex=1)
```

详见 `references/09-multi-portfolio.md`。

---

## `Slippage`（滑点）类型

### `FixedSlippage(value)`

固定滑点（绝对值，单位元）：

```python
set_slippage(FixedSlippage(0.02))     # 0.02 元 / 股
```

### `PriceRelatedSlippage(value)`

价格相关滑点（相对当前价的比例）：

```python
set_slippage(PriceRelatedSlippage(0.00246))   # 0.246%
```

### `StepRelatedSlippage(value)`

按价格变动单位（最小价格步长）滑点。期货常用。

```python
set_slippage(StepRelatedSlippage(2))   # 2 个最小变动单位
```

---

## `SecurityUnitData`（单标的某根 bar 的数据）

`history()` / `attribute_history()` / `get_price()` 等返回的 DataFrame 元素。

属性：
- `open` / `close` / `high` / `low` — OHLC
- `volume` — 成交量
- `money` — 成交额
- `pre_close` — 上一交易日收盘
- `factor` — 复权因子
- `mavg(N)` — N 周期移动均线
- `vwap(N)` — N 周期 vwap

---

## 必背规则

1. ⚠️ **判断持仓用 `total_amount > 0`，不要用 `if pos`**（pos 可能存在但 amount = 0）
2. ⚠️ **可卖数量用 `closeable_amount`**——A 股 T+1，刚买的不能卖
3. ⚠️ **下单返回的 Order 可能是 None**——下单失败时
4. ⚠️ **手续费类型要选对**——`type='stock'` vs `type='index_futures'` 算法完全不同
5. ⚠️ **限价单挂单后会一直留**——记得清理过期订单（`cancel_order`）

---

## AI 常编错的属性

| AI 编的 | 实际应该用 |
|---|---|
| `position.amount` | `position.total_amount` |
| `position.cost_price` | `position.avg_cost` |
| `position.market_value` | `position.value` |
| `portfolio.cash_balance` | `portfolio.available_cash` |
| `portfolio.holdings` | `portfolio.positions` |
| `order.id` | `order.order_id` |
| `order.quantity` | `order.amount` |
| `order.filled_quantity` | `order.filled` |
