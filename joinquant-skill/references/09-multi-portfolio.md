# 09 — 多投资组合（多账户）

> 在一个策略中管理多个子账户，支持股票、期货、融资融券混合配置。

## set_subportfolios ★

```python
set_subportfolios([SubPortfolioConfig(cash, type), ...])
```

初始化或修改子账户配置。**只能在 `initialize` 中调用**。

所有 `SubPortfolioConfig` 的 `cash` 之和必须等于总初始资金。

### SubPortfolioConfig

```python
SubPortfolioConfig(cash, type)
```

**参数**：
- `cash`：该仓位的初始资金
- `type`：可操作标的类型
  - `'stock'`：股票和基金
  - `'index_futures'`：金融期货（股指期货）
  - `'futures'`：所有期货（含商品期货和股指期货）
  - `'stock_margin'`：融资融券账户

### 示例

```python
def initialize(context):
    init_cash = context.portfolio.starting_cash / 3
    set_subportfolios([
        SubPortfolioConfig(cash=init_cash, type='stock'),
        SubPortfolioConfig(cash=init_cash, type='futures'),
        SubPortfolioConfig(cash=init_cash, type='stock_margin'),
    ])
```

---

## transfer_cash 账户间转移资金

```python
transfer_cash(from_pindex, to_pindex, cash)
```

资金即时到账。

```python
transfer_cash(from_pindex=0, to_pindex=1, cash=500000)
```

---

## SubPortfolio 对象

每个子账户的信息。通过 `context.subportfolios[i]` 访问。

如果不使用 `set_subportfolios`，默认只有 `subportfolios[0]`，`Portfolio` 指向该仓位。

每个策略最多创建 **100** 个 subportfolio。

### 常用属性

| 属性 | 说明 |
|---|---|
| `cash` | 可用现金 |
| `positions` | 持仓字典 |
| `total_value` | 总价值 |
| `available_cash` | 可用资金 |
| `locked_cash` | 冻结资金 |
| `type` | 账户类型 |

---

## 多账户下单

下单函数通过 `pindex` 参数指定操作哪个子账户：

```python
order('000001.XSHE', 100, pindex=0)          # 在子账户0买股票
order('IF2106.CCFX', 1, side='long', pindex=1)  # 在子账户1开期货多单
margincash_open('000001.XSHE', 1000, pindex=2)   # 在子账户2融资买入
```

**所有下单函数**（`order`, `order_value`, `order_target`, `order_target_value` 等）都支持 `pindex` 参数。

---

## 典型应用场景

### 股票 + 期货对冲

```python
def initialize(context):
    total = context.portfolio.starting_cash
    set_subportfolios([
        SubPortfolioConfig(cash=total * 0.8, type='stock'),
        SubPortfolioConfig(cash=total * 0.2, type='futures'),
    ])
    run_daily(hedge, time='09:31')

def hedge(context):
    # 子账户0：买股票
    order_value('000001.XSHE', 100000, pindex=0)
    # 子账户1：空股指期货对冲
    order('IF2106.CCFX', 1, side='short', pindex=1)
```

### 资金再平衡

```python
def rebalance(context):
    sp0 = context.subportfolios[0]
    sp1 = context.subportfolios[1]
    diff = sp0.total_value - sp1.total_value
    if diff > 100000:
        transfer_cash(0, 1, diff / 2)
    elif diff < -100000:
        transfer_cash(1, 0, abs(diff) / 2)
```

---

## 常见失败模式

❌ 在 `handle_data` 中调用 `set_subportfolios` → 只能在 `initialize` 中调用
❌ `cash` 之和不等于初始资金 → 会报错
❌ `pindex` 超出范围 → 如只设了 2 个子账户，`pindex=2` 会失败
❌ 在 `type='stock'` 的账户中下期货单 → 类型不匹配
❌ `set_subportfolios` 设置超过 100 个 → 超出限制
