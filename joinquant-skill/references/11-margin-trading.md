# 11 — 融资融券

> 聚宽支持融资买入、融券卖出、直接还款还券等两融操作。需初始化为 `stock_margin` 类型账户。

## 初始化融资融券账户 ★

默认账户 `type='stock'` 不允许两融操作。必须设置 `type='stock_margin'`：

```python
def initialize(context):
    init_cash = context.portfolio.starting_cash
    set_subportfolios([SubPortfolioConfig(cash=init_cash, type='stock_margin')])
```

**多账户混合**：
```python
def initialize(context):
    init_cash = context.portfolio.starting_cash / 3
    set_subportfolios([
        SubPortfolioConfig(cash=init_cash, type='stock'),
        SubPortfolioConfig(cash=init_cash, type='index_futures'),
        SubPortfolioConfig(cash=init_cash, type='stock_margin'),
    ])
```

---

## 利率和保证金设置

```python
set_option('margincash_interest_rate', 0.08)   # 融资利率，默认 8%
set_option('margincash_margin_rate', 1.5)      # 融资保证金比率，默认 100%
set_option('marginsec_interest_rate', 0.10)    # 融券利率，默认 10%
set_option('marginsec_margin_rate', 1.5)       # 融券保证金比率，默认 100%
```

---

## 融资操作

### margincash_open 融资买入

```python
margincash_open(security, amount, style=None, pindex=0)
```

```python
margincash_open('000001.XSHE', 1000)
```

### margincash_close 卖券还款

```python
margincash_close(security, amount, style=None, pindex=0)
```

```python
margincash_close('000001.XSHE', 1000)
```

### margincash_direct_refund 直接还款

```python
margincash_direct_refund(value, pindex=0)
```

```python
margincash_direct_refund(100000)
```

---

## 融券操作

### marginsec_open 融券卖出

```python
marginsec_open(security, amount, style=None, pindex=0)
```

```python
marginsec_open('000001.XSHE', 1000)
```

### marginsec_close 买券还券

```python
marginsec_close(security, amount, style=None, pindex=0)
```

```python
marginsec_close('000001.XSHE', 1000)
```

### marginsec_direct_refund 直接还券

```python
marginsec_direct_refund(security, amount, pindex=0)
```

需要账户中有足够持仓：
```python
# 如果持仓中有 1000 股
marginsec_direct_refund('000001.XSHE', 1000)

# 如果没有，先买入再还
order('000001.XSHE', 1000)
marginsec_direct_refund('000001.XSHE', 1000)
```

---

## 融资融券标的查询

### get_margincash_stocks 融资标的列表

```python
margincash_stocks = get_margincash_stocks()
'000001.XSHE' in get_margincash_stocks()  # True
```

### get_marginsec_stocks 融券标的列表

```python
marginsec_stocks = get_marginsec_stocks(date=None)
'000001.XSHE' in get_marginsec_stocks()  # True
```

**注意**：无法获取当前未完结交易日的数据（交易所数据尚未生成）。

### get_mtss 融资融券信息

```python
from jqdata import *

get_mtss(security_list, start_date=None, end_date=None, fields=None, count=None)
```

**返回字段**：

| 字段 | 含义 |
|---|---|
| `date` | 日期 |
| `sec_code` | 股票代码 |
| `fin_value` | 融资余额（元） |
| `fin_buy_value` | 融资买入额（元） |
| `fin_refund_value` | 融资偿还额（元） |
| `sec_value` | 融券余量（股） |
| `sec_sell_value` | 融券卖出量（股） |
| `sec_refund_value` | 融券偿还量（股） |
| `fin_sec_value` | 融资融券余额（元） |

```python
from jqdata import *

get_mtss('000001.XSHE', '2016-01-01', '2016-04-01')
get_mtss(['000001.XSHE', '000002.XSHE'], '2015-03-25', '2016-01-25',
         fields=['date', 'sec_code', 'fin_value'])
get_mtss('000001.XSHE', end_date='2016-06-30', count=20)
```

---

## 常见失败模式

❌ 在 `type='stock'` 账户中调用 `margincash_open` → 类型不匹配
❌ 混淆 `margincash_close`（卖券还款）和 `margincash_direct_refund`（直接现金还款）
❌ `marginsec_direct_refund` 时持仓不足 → 需先买入
❌ `get_margincash_stocks()` 获取当天数据 → 交易日未结束时数据不可用
❌ 忘记 `from jqdata import *` 就调用 `get_mtss` → 需要导入
