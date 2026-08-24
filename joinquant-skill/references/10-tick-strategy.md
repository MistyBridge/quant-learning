# 10 — Tick 级策略

> Tick 级策略在每个 Tick 快照到达时执行一次，适合高频或短线交易。需要权限。

## 前置条件

- **需要 Tick 权限**：会员或积分兑换
- **必须开启真实价格模式**：`set_option('use_real_price', True)`
- **`handle_data` 和 `run_daily(..., 'every_bar')` 不会在 Tick 策略中调用**

## 数据支持

| 标的类型 | 数据起始时间 | Tick 间隔 | 盘口深度 |
|---|---|---|---|
| 股票 | 2017-01-01 | 3 秒 | 买五卖五 |
| 期货 | 2010-01-01 | 0.5 秒 | 买一卖一 |
| 场内基金 | 2019-01-01 | 3 秒 | 买五卖五 |
| 指数 | 2017-01-01 | 3 秒 | 无 |

---

## handle_tick ★

```python
def handle_tick(context, tick):
    log.info(tick)
```

当订阅的标的产生 Tick 事件时被调用。没有 Tick 事件则不调用。

**参数**：
- `context`：Context 对象
- `tick`：Tick 对象，包含触发事件的 Tick 数据

---

## subscribe 订阅 Tick

```python
subscribe(security, frequency)
```

**参数**：
- `security`：标的代码或代码列表。支持股票、期货、中证指数、场内基金。**不能直接订阅主力合约或期货指数代码**
- `frequency`：目前必须为 `'tick'`

**限制**：
- 回测中不限订阅数量
- 模拟交易中最多同时订阅 **100** 个标的

---

## unsubscribe 取消订阅

```python
unsubscribe(security, frequency)
```

## unsubscribe_all 取消全部订阅

```python
unsubscribe_all()
```

---

## 示例：期货 Tick 策略

```python
def initialize(context):
    init_cash = context.portfolio.starting_cash
    set_subportfolios([SubPortfolioConfig(cash=init_cash, type='futures')])
    g.code1 = 'RB1909.XSGE'
    run_daily(before_market_open, time='08:30', reference_security='RB9999.XSGE')
    run_daily(after_market_close, time='15:30', reference_security='RB9999.XSGE')

def before_market_open(context):
    subscribe(g.code1, 'tick')

def handle_tick(context, tick):
    tick_data = get_current_tick(g.code1)
    print(tick_data)

def after_market_close(context):
    unsubscribe_all()
```

## 示例：股票 Tick 策略

```python
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        close_tax=0.001, open_commission=0.0003,
        close_commission=0.0003, min_commission=5
    ), type='stock')

def before_trading_start(context):
    subscribe('000001.XSHE', 'tick')

def handle_tick(context, tick):
    log.info(tick)

def after_trading_end(context):
    unsubscribe_all()
```

---

## Tick 撮合逻辑

- 市价单：按最新价+滑点撮合（或启用盘口撮合时按对手盘）
- 限价单：每个 Tick 尝试撮合，委托价满足条件时以委托价成交
- 按 Tick 撮合时**不检查成交量**，满足价格条件后剩余部分全部成交

---

## 常见失败模式

❌ 没开 `use_real_price` → Tick 回测必须使用真实价格模式
❌ 在 Tick 策略中写 `handle_data` 期望被调用 → 不会被调用
❌ `subscribe('IF9999.CCFX', 'tick')` → 不能订阅主力合约代码，要用具体合约
❌ 模拟交易中订阅超过 100 个标的 → 超出限制
❌ 在 `after_trading_end` 中没有 `unsubscribe_all()` → 下一天可能残留订阅
