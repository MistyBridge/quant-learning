# 02 — 数据获取函数

> 聚宽里所有"取价格、取财务、取因子"的入口。**最易出错的一类**——AI 经常编造不存在的 `get_stock_data` / `get_history_data`。

---

## 价格类（最常用）

### `get_price(security, ...)` ★

最核心的取价 API。

```python
df = get_price(
    security='000001.XSHE',     # 单标的或 list
    start_date='2023-01-01',
    end_date='2023-12-31',
    frequency='daily',           # 'daily' / 'minute' / '1m' / '5m' / '60m' / 'tick'
    fields=['open', 'close', 'high', 'low', 'volume', 'money'],
    skip_paused=False,           # True 跳过停牌
    fq='pre',                    # 'pre'前复权 / 'post'后复权 / None 不复权
    count=None,                  # 与 start_date 二选一
    panel=False,                 # 多标的时返回 panel 还是 dict
    fill_paused=True,            # 停牌日是否填充上一日
)
```

**返回**：DataFrame（单标的）/ Panel/dict（多标的）

**关键提醒**：
- ⚠️ `start_date` 和 `count` 互斥
- ⚠️ 在回测里用 `count` 而不是硬编码 `start_date`，避免未来函数
- ⚠️ `frequency='tick'` 只在 tick 级回测可用
- ⚠️ `fq` 参数：研究环境默认 `'pre'`，回测里如果开了 `use_real_price=True`，价格已经是真实价格

### `attribute_history(security, count, unit, fields, ...)` ★

回测里用得最多。**默认从当前时间往回取，自动避免未来函数**。

```python
df = attribute_history(
    security='000001.XSHE',
    count=20,                # 取多少根
    unit='1d',                # '1d' / '1m' / '5m' / '15m' / '30m' / '60m' / '120m'
    fields=['close', 'volume'],
    skip_paused=True,
    df=True,
    fq='pre',
)
```

**vs `get_price`**：`attribute_history` 不要传 date，自动从 `context.current_dt` 倒推 N 根。**首选这个**。

### `history(count, unit, field, security_list, ...)`

`attribute_history` 的多标的版。

```python
df = history(
    count=20, unit='1d', field='close',
    security_list=['000001.XSHE', '000002.XSHE'],
)
# df 列是股票代码，行是时间
```

### `get_current_data()` ★

取**当前 tick** 的实时数据（高开低收 + 涨跌停 + 最新价）。

```python
cd = get_current_data()
print(cd['000001.XSHE'].last_price)
print(cd['000001.XSHE'].high_limit)   # 涨停价
print(cd['000001.XSHE'].low_limit)    # 跌停价
print(cd['000001.XSHE'].paused)       # 是否停牌
print(cd['000001.XSHE'].is_st)        # 是否 ST
```

**用途**：判断涨跌停、停牌、ST 等。

---

## 财务数据

### `get_fundamentals(query_obj, date=None)` ★

取财务数据（PE / 市值 / 利润等）。需要构造 `query` 对象：

```python
q = query(
    valuation.code,
    valuation.pe_ratio,
    valuation.market_cap,
    indicator.roe,
).filter(
    valuation.code.in_(stocks)
).order_by(
    valuation.market_cap.asc()
).limit(50)

df = get_fundamentals(q)
```

**字段命名空间**：
- `valuation.*` —— 估值（pe, pb, market_cap, ps, ...）
- `balance.*` —— 资产负债表
- `income.*` —— 利润表
- `cash_flow.*` —— 现金流量表
- `indicator.*` —— 财务指标（roe, roa, eps, ...）

完整字段见聚宽官方 API 文档（`api文档/api.txt` 里搜对应章节）。

### `get_factor_values(securities, factors, end_date, count)` ★

取**聚宽因子库**的值（已经预计算的因子，比自己算快得多）。

```python
factors = ['pe_ratio', 'momentum_20d', 'volatility_60d']
fv = get_factor_values(
    securities=['000001.XSHE', '000002.XSHE'],
    factors=factors,
    end_date='2023-06-30',
    count=10,
)
# fv 是 dict，key 是因子名，value 是 DataFrame（行=日期，列=股票）
```

---

## 股票池 / 标的池

### `get_index_stocks(index_code, date=None)`

取指数成分股。

```python
hs300 = get_index_stocks('000300.XSHG')
zz500 = get_index_stocks('000905.XSHG')
```

### `get_industry_stocks(industry_code, date=None)`

取某行业成分股。

```python
banks = get_industry_stocks('801780')  # 申万银行
```

### `get_concept_stocks(concept_code, date=None)`

取某概念板块成分股。

```python
ai_stocks = get_concept_stocks('GN034')  # AI 概念
```

### `get_all_securities(types, date=None)` ★

取所有标的。`types` 可以是：
- `'stock'` 股票
- `'fund'` 基金
- `'index'` 指数
- `'futures'` 期货
- `'options'` 期权

```python
all_stocks = get_all_securities(['stock'])
# 返回 DataFrame，索引是代码，列有 display_name / start_date / end_date
```

### `get_security_info(code)`

取某只标的详细信息。

```python
info = get_security_info('000001.XSHE')
print(info.display_name, info.start_date, info.end_date)
```

---

## 行业 / 概念分类

### `get_industry(security, date=None)` ★

取股票所属行业（聚宽行业 / 申万 / 国证）。

```python
ind = get_industry('000001.XSHE')
print(ind['000001.XSHE']['jq_l1'])   # 聚宽一级行业
print(ind['000001.XSHE']['sw_l1'])   # 申万一级
```

### `get_concept(security, date=None)`

取股票所属概念。

```python
con = get_concept('000001.XSHE')
print(con['000001.XSHE']['jq_concept'])
```

---

## 其他常用

### `get_money_flow(security_list, start_date, end_date, fields, count)`

资金流向（主力净额、超大单、大单等），仅股票，2010 年至今日频。

### `get_call_auction(security, start_date, end_date, fields)`

集合竞价 09:25 的 tick 数据（含五档买卖盘）。

### `get_all_trade_days()` / `get_trade_days(start_date, end_date)`

取交易日列表。

### `get_extras(info, security_list, ...)`

取除权除息、是否 ST、退市状态等扩展信息。

### `get_locked_shares(stock_list, start_date, end_date)`

取限售解禁数据。

### `get_ticks(security, end_dt, count, fields)`

取 tick 级数据。**只在 tick 级回测/模拟可用**。

---

## 期货专用

### `get_dominant_future(underlying_symbol, date=None)`

取主力合约。

```python
ifc = get_dominant_future('IF', date='2023-06-30')  # 'IF2306.CCFX'
```

### `get_future_contracts(underlying_symbol, date=None)`

取所有合约。

详见 `references/12-futures.md`。

---

## 必背规则

1. ⚠️ **回测里取历史数据，首选 `attribute_history` 而不是 `get_price`**——前者自动避免未来函数
2. ⚠️ **多标的取数据时用 panel/dict 模式，不要 for 循环**——性能差很多
3. ⚠️ **`fq` 参数和 `set_option('use_real_price', True)` 的关系**：开启真实价格后，所有取价 API 自动按当日复权因子前复权
4. ⚠️ **聚宽预计算因子比自己算快**：能用 `get_factor_values` 就别用 `get_fundamentals` + 手算
5. ⚠️ **financial query 的 limit 默认 100**——大池子要显式指定 `.limit(N)`

---

## AI 常编错的 API

| AI 编的 | 实际应该用 |
|---|---|
| `get_stock_data(code)` | `get_price(code, ...)` 或 `attribute_history(code, ...)` |
| `get_history_data(code, days)` | `attribute_history(code, days, '1d', ['close'])` |
| `jqdata.fetch_data(...)` | 不存在的命名空间，直接用 `get_price` |
| `get_realtime_quote(code)` | `get_current_data()[code].last_price` |
| `get_index_constituents('hs300')` | `get_index_stocks('000300.XSHG')` |
| `get_account_balance()` | `context.portfolio.available_cash` |
| `get_position(code)` | `context.portfolio.positions.get(code)` |
