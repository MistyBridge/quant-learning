# 01 — 策略设置函数

> 这是聚宽策略代码的"骨架"。每个策略都必须实现 `initialize`，并在里面调用必备的 set 系列函数。

## 必须实现的策略入口函数

### `initialize(context)` ★

**调用时机**：策略启动时（回测/模拟/实盘）只调用一次。

**职责**：
- 设置基准、复权模式、税费、滑点
- 初始化全局变量（用 `g.xxx`）
- 注册定时任务（`run_daily` / `run_weekly` / `run_monthly`）

**示例**：
```python
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(FixedSlippage(0.02))
    g.security = '000001.XSHE'
    run_daily(trade, time='open')
```

### `before_trading_start(context)`

**调用时机**：每个交易日开盘前 09:30 之前。
**用途**：选股、设置今日目标。
**注意**：**禁止下单**。下单必须放到 `handle_data` 或 `run_daily` 调度的函数。

### `handle_data(context, data)`

**调用时机**：分钟回测每分钟、日回测每日。
**注意**：现在更推荐用 `run_daily(func, time=...)` 替代直接写 `handle_data`。

### `after_trading_end(context)`

**调用时机**：每个交易日收盘后 15:30 之后。
**用途**：日终统计、打印日志。
**注意**：**禁止下单**。

---

## 配置类函数（在 `initialize` 里调用）

### `set_benchmark(security)` ★

设置基准指数。**必填**。常用：`'000300.XSHG'`（沪深 300）、`'000905.XSHG'`（中证 500）。

### `set_option(option, value)` ★

设置回测/模拟选项。**最关键**：

```python
set_option('use_real_price', True)        # 必开！避免未来函数
set_option('order_volume_ratio', 0.25)    # 单笔订单成交不超过当日总量的 25%
set_option('avoid_future_data', True)     # 默认开启
```

### `set_order_cost(cost, type)` ★

设置交易税费。`type` 有 `'stock'`、`'fund'`、`'mmf'`、`'index_futures'` 等。

```python
set_order_cost(OrderCost(
    open_tax=0,                # 买入印花税（A股为 0）
    close_tax=0.001,           # 卖出印花税 0.1%
    open_commission=0.0003,    # 买入手续费万 3
    close_commission=0.0003,   # 卖出手续费万 3
    close_today_commission=0,  # 平今手续费（股票为 0，期货才有）
    min_commission=5,          # 最低收费 5 元
), type='stock')
```

### `set_slippage(slippage)` ★

设置滑点。两种类型：

```python
# 固定滑点（绝对值）
set_slippage(FixedSlippage(0.02))

# 价格相关滑点（百分比）
set_slippage(PriceRelatedSlippage(0.00246))
```

### `set_universe(securities)`

旧 API，已不推荐。建议在 `before_trading_start` 中动态选股。

---

## 调度函数

### `run_daily(func, time)` ★

```python
run_daily(market_open, time='open')        # 09:30 开盘
run_daily(market_close, time='before_close') # 14:50 尾盘
run_daily(intraday, time='every_bar')       # 每根 bar
run_daily(custom, time='14:30')             # 自定义时间
```

### `run_weekly(func, weekday, time)`

```python
run_weekly(rebalance, weekday=1, time='09:31')  # 每周一 09:31
```

### `run_monthly(func, monthday, time)`

```python
run_monthly(rebalance, monthday=1, time='09:31')  # 每月第 1 个交易日 09:31
```

`monthday=-1` 表示每月最后一个交易日。

---

## 多投资组合（高级）

```python
set_subportfolios([
    SubPortfolioConfig(cash=500000, type='stock'),
    SubPortfolioConfig(cash=500000, type='index_futures'),
])
```

详见 `references/09-multi-portfolio.md`。

---

## 期货 / 融资融券额外设置

参见对应专门文档：
- `references/12-futures.md`
- `references/11-margin-trading.md`

---

## 检查清单（lint 工具会查）

| 项 | 必填 | 不设的后果 |
|---|---|---|
| `set_benchmark` | ✅ | 无法计算 alpha / beta / 信息比率 |
| `set_option('use_real_price', True)` | ✅ | 回测有未来函数偏差 |
| `set_order_cost(...)` | ✅ | 用聚宽默认费率，与你实际券商可能差很远 |
| `set_slippage(...)` | ✅ | 回测无滑点，过于乐观 |

下单类函数禁止出现在：
- `before_trading_start`
- `after_trading_end`
- 全局作用域（必须在函数里）

---

## 常见失败模式

❌ `set_initial_cash(...)` —— 不存在的 API。初始资金在聚宽 Web 界面设置  
❌ 没有 `set_benchmark` —— 无法和大盘对比  
❌ `set_universe(['000001.XSHE'])` 然后期望它自动随时间变化 —— 它不会，得在 `before_trading_start` 动态算  
❌ `run_daily(func)` 没传 `time` —— 默认 `'open'`，可能不是你想要的
