# 06 — 交易函数

> 所有"下单 / 撤单 / 查订单"相关的 API。**必须在交易时间调用**——禁止在 `before_trading_start` / `after_trading_end` 中下单。

## 主下单函数

### `order(security, amount, style=None, side='long', pindex=0)` ★

按数量下单。

```python
order('000001.XSHE', 1000)           # 买入 1000 股平安银行
order('000001.XSHE', -1000)          # 卖出 1000 股
order('000001.XSHE', 1000, LimitOrderStyle(15.0))  # 限价单 15 元
order('000001.XSHE', 1000, side='short')  # 融券卖空
```

**返回**：`Order` 对象（成功）/ `None`（失败）

**注意**：amount 必须是 100 的整数倍（A 股一手）。下单 50 会报错。

### `order_value(security, value, style=None, side='long', pindex=0)` ★

按金额下单（**推荐**）。

```python
order_value('000001.XSHE', 50000)    # 买入 50000 元的平安银行
order_value('000001.XSHE', -30000)   # 卖出 30000 元
```

**为什么推荐**：自动按当前价计算 amount，并向下取整到 100 股的整数倍。比手算除法更安全。

### `order_target(security, amount, style=None, side='long', pindex=0)` ★

调整目标持仓数量。

```python
order_target('000001.XSHE', 0)       # 清仓
order_target('000001.XSHE', 1000)    # 调整到 1000 股
```

**用途**：调仓最常用。`order_target(s, 0)` = 卖光 s。

### `order_target_value(security, value, style=None, side='long', pindex=0)` ★

调整目标持仓**金额**。

```python
order_target_value('000001.XSHE', 50000)  # 调到 50000 元
order_target_value('000001.XSHE', 0)      # 清仓
```

**为什么推荐**：等权重多股票调仓时，直接 `order_target_value(s, total/N)`。

### `order_market(security, amount, side='long', pindex=0)`

市价单。等价于 `order(security, amount)`（默认就是市价单）。

### `order_lots(security, lots, style=None, ...)`

按手数下单（1 手 = 100 股）。

```python
order_lots('000001.XSHE', 10)   # 买 10 手 = 1000 股
```

---

## 订单查询 / 取消

### `get_open_orders(security=None)`

查询未完成订单。

```python
open_orders = get_open_orders()
for order in open_orders.values():
    print(order.order_id, order.security, order.amount, order.status)
```

**返回**：dict，key 是 order_id，value 是 `Order` 对象。

### `get_orders(security=None, status='all')`

查询订单（含已完成）。`status` 可以是 `'open'` / `'filled'` / `'canceled'` / `'all'`。

### `get_trades()`

查询本日成交记录。

### `cancel_order(order)`

取消订单。

```python
open_orders = get_open_orders()
for order_id, order in open_orders.items():
    if order.security == '000001.XSHE':
        cancel_order(order)
```

可以传 `order_id` 字符串或 `Order` 对象。

---

## 期货专用

### `buy_open(security, amount, style=None, pindex=0)` / `sell_open(...)`

期货开仓（buy 多头 / sell 空头）。

### `buy_close(security, amount, style=None, close_today=False, pindex=0)` / `sell_close(...)`

期货平仓。`close_today=True` 表示平今仓（注意手续费可能不一样）。

详见 `references/12-futures.md`。

---

## 融资融券专用

### `margincash_open(security, amount, style=None, pindex=0)`

融资买入。

### `margincash_close(security, amount, style=None, pindex=0)`

卖券还款。

### `margincash_direct_refund(value, pindex=0)`

直接还款。

### `marginsec_open(security, amount, style=None, pindex=0)`

融券卖出。

### `marginsec_close(security, amount, style=None, pindex=0)`

买券还券。

详见 `references/11-margin-trading.md`。

---

## OrderStyle（订单类型）

### `MarketOrderStyle(price=None)`

市价单（默认）。

### `LimitOrderStyle(limit_price)`

限价单。

```python
order('000001.XSHE', 1000, LimitOrderStyle(15.0))   # 限价 15 元买
order('000001.XSHE', -1000, LimitOrderStyle(20.0))  # 限价 20 元卖
```

详见 `references/07-objects.md`。

---

## 撮合规则要点（来自 14-strategy-engine.md）

- **市价单**：按 `最新价 + 滑点` 撮合
- **限价单**：下单时尝试按最新价撮合，剩余部分挂单，每分钟 bar 结束时尝试按 bar 信息撮合
- **涨停时**：市价买单会被撤销
- **跌停时**：市价卖单会被撤销

详见 `references/14-strategy-engine.md`。

---

## 多投资组合下单

如果用了 `set_subportfolios([...])`，下单时要指定 `pindex`：

```python
order('000001.XSHE', 1000, pindex=0)  # 第一个 sub-portfolio
order('IF2306.CCFX', 1, pindex=1)     # 第二个 sub-portfolio
```

详见 `references/09-multi-portfolio.md`。

---

## 必背规则

1. ⚠️ **优先用 `order_value` / `order_target_value`，不要手动算 amount**
2. ⚠️ **A 股 amount 必须是 100 的整数倍**（`order_value` 会自动处理）
3. ⚠️ **不要在 `before_trading_start` / `after_trading_end` 下单**——会报错
4. ⚠️ **同一只股票不能同时挂买单和卖单**——会冲突
5. ⚠️ **`order_target(s, 0)` 是清仓的最简单写法**

---

## AI 常编错的下单 API

| AI 编的 | 实际应该用 |
|---|---|
| `place_order(...)` | `order(...)` 或 `order_value(...)` |
| `submit_order(...)` | `order(...)` |
| `buy_stock(s, n)` | `order(s, n)` |
| `sell_stock(s, n)` | `order(s, -n)` |
| `set_position(s, value)` | `order_target_value(s, value)` |
| `close_position(s)` | `order_target(s, 0)` |
