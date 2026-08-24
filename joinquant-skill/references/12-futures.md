# 12 — 期货策略

> 聚宽支持商品期货和金融期货（股指期货）。需初始化为 `futures` 类型账户。

## 初始化期货账户 ★

默认账户只能买卖股票和基金。必须设置 `type='futures'`：

```python
def initialize(context):
    init_cash = context.portfolio.starting_cash
    set_subportfolios([SubPortfolioConfig(cash=init_cash, type='futures')])
    run_daily(market_open, time='every_bar', reference_security='CU9999.XSGE')
```

---

## 合约代码规则

| 类型 | 格式 | 示例 | 说明 |
|---|---|---|---|
| 具体合约 | 品种+年月.交易所 | `RB1909.XSGE` | 可下单 |
| 主力连续 | 品种+9999.交易所 | `AG9999.XSGE` | **不可下单**，仅查数据 |
| 品种指数 | 品种+8888.交易所 | `AG8888.XSGE` | **不可下单**，仅查数据 |

### 主力合约规则
- 持仓量连续 2 天为同品种最大（金融期货限最近两个合约）
- 必须为当前主力的远期合约
- 不在日内切换

---

## get_dominant_future 获取主力合约

```python
get_dominant_future(underlying_symbol, date=None)
```

```python
get_dominant_future('IF')  # → 'IF1608.CCFX'
get_dominant_future('AG')  # → 'AG2106.XSGE'
```

## get_future_contracts 可交易合约列表

```python
get_future_contracts(security, date=None)
```

```python
get_future_contracts('IF')
# ['IF1606.CCFX', 'IF1607.CCFX', 'IF1609.CCFX', 'IF1612.CCFX']
```

---

## 保证金设置

```python
set_option('futures_margin_rate', 0.25)           # 所有期货 25%
set_option('futures_margin_rate.AU1709', 0.08)     # 黄金 AU1709 合约 8%
set_option('futures_margin_rate.AU', 0.09)         # 所有黄金期货 9%
set_option('futures_margin_rate.IF', 0.15)         # 所有股指期货 15%
```

**默认保证金比例**：股指期货 15%，商品期货按品种不同在 4%~20% 之间。

### is_dangerous 保证金预警

```python
context.subportfolios[i].is_dangerous(margin_rate)
```

```python
context.subportfolios[1].is_dangerous(0.2)
# 保证金低于 20% 返回 True
```

---

## 期货下单函数

所有下单函数都增加了 `side` 和 `close_today` 参数：

### order 按手数下单

```python
order(security, amount, style=None, side='long', pindex=0, close_today=False)
```

```python
order('IF1412.CCFX', 1, side='short', pindex=0)    # 开空单
order('IF1412.CCFX', 1, side='long', pindex=0)     # 开多单
order('IF1412.CCFX', -1, side='long', pindex=1)    # 平多单
order('IF1412.CCFX', -1, LimitOrderStyle(3600.0), side='short', pindex=1)  # 限价平空
```

### order_target 目标手数下单

```python
order_target(security, amount, style=None, side='long', pindex=0, close_today=False)
```

```python
order_target('IF1412.CCFX', 5, side='long', pindex=1)   # 多单调整到5手
order_target('IF1412.CCFX', 4, side='long', pindex=1)   # 平1手多单
order_target('IF1412.CCFX', 0, side='long', pindex=1)   # 平掉所有多单
```

### order_value 按保证金下单

```python
order_value(security, value, style=None, side='long', pindex=0, close_today=False)
```

`value = 最新价 × 手数 × 保证金率 × 乘数`

```python
order_value('IF1412.CCFX', 5000000, side='long', pindex=1)   # 开多
order_value('IF1412.CCFX', -4000000, side='long', pindex=1)  # 平多
```

### order_target_value 目标保证金下单

```python
order_target_value(security, value, style=None, side='long', pindex=0, close_today=False)
```

```python
order_target_value('IF1412.CCFX', 5000000, side='long', pindex=1)
order_target_value('IF1412.CCFX', 0, side='long', pindex=1)  # 全平
```

---

## close_today 平今参数

仅对以下交易所生效：
- 上海国际能源中心
- 上海期货交易所
- 中金所

| 值 | 行为 |
|---|---|
| `True` | 只平今仓 |
| `False`（默认） | 优先平昨仓，不足部分平今仓 |

其他交易所使用 `close_today` 会报错（它们按先开先平处理）。

---

## 期货注意事项

- 有夜盘的商品期货一个交易日从前一天 21:00 开始
- 每日 16:00 结算，使用结算价
- 持仓到交割日系统自动以结算价平仓（无手续费、无交易记录）
- 股指期货平今手续费默认万分之六点九
- `get_price` 等行情 API 新增 `open_interest`（持仓量）字段
- `pre_close` 在天数据中为前结算价

---

## 常见失败模式

❌ 在 `type='stock'` 账户中买期货 → 需要 `type='futures'`
❌ 对主力合约 `IF9999.CCFX` 直接下单 → 不可下单，要用 `get_dominant_future` 获取具体合约
❌ 在非上期所/中金所品种上使用 `close_today=True` → 会报错
❌ 忘记设置 `reference_security` → `run_daily` 需要期货类型的参考标的
❌ 混淆 `side='long'` 和正负 `amount` → `amount` 正=开仓/负=平仓，`side` 指多空方向
