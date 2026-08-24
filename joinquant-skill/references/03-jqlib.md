# 03 — jqlib 因子库

> 聚宽内置的因子计算库，包含 Alpha101、Alpha191 和技术分析指标三大模块。所有函数均在聚宽策略/研究环境中直接可用。

## Alpha 101

来源：WorldQuant LLC 论文 *101 Formulaic Alphas*。

```python
from jqlib.alpha101 import *

# 获取沪深300成分股的 alpha_001 因子值
a = alpha_001('2017-03-10', '000300.XSHG')
a.head()
# 000001.XSHE   -0.496667
# 000002.XSHE    0.226667
# ...

# 查看单只股票
a['000001.XSHE']
```

**函数签名**：`alpha_NNN(enddate, index=None)`
- `enddate`：查询日期（字符串）
- `index`：股票池，可选。传指数代码则取该指数成分股

共 101 个函数 (`alpha_001` ~ `alpha_101`)。

---

## Alpha 191

来源：国泰君安《基于短周期价量特征的多因子选股体系》。

```python
from jqlib.alpha191 import *

end_date = '2017-04-04'
code = list(get_all_securities(['stock'], date=end_date).index)
a = alpha_007(code, end_date)
a['300207.XSHE']
```

**函数签名**：`alpha_NNN(code, end_date=None)`
- `code`：股票池（列表）
- `end_date`：查询日期

共 191 个函数 (`alpha_001` ~ `alpha_191`)。

### Alpha101 vs Alpha191 区别

| | Alpha 101 | Alpha 191 |
|---|---|---|
| 第一个参数 | `enddate`（日期） | `code`（股票列表） |
| 第二个参数 | `index`（指数代码，可选） | `end_date`（日期，可选） |
| 来源 | WorldQuant | 国泰君安 |

---

## technical_analysis 技术分析指标

基于通达信、东方财富、同花顺公式实现。

```python
from jqlib.technical_analysis import *

security_list1 = '000001.XSHE'
security_list2 = ['000001.XSHE', '000002.XSHE', '601211.XSHG', '603177.XSHG']

# 济安线指标 GDX
gdx_jax, gdx_ylx, gdx_zcx = GDX(security_list1, check_date='2017-01-04', N=30, M=9)
print(gdx_jax[security_list1])
print(gdx_ylx[security_list1])
print(gdx_zcx[security_list1])

# 批量计算
gdx_jax, gdx_ylx, gdx_zcx = GDX(security_list2, check_date='2017-01-04', N=30, M=9)
for stock in security_list2:
    print(gdx_jax[stock])
```

**通用签名**：`INDICATOR(security_list, check_date, ...)`

返回值类型：`dict`，key 为股票代码，value 为数据值。

完整指标列表和公式见 [数据字典 - 技术分析指标](https://www.joinquant.com/help/api/helpname=technicalanalysis)。

### 注意事项

- 技术指标常见问题：动态复权与技术指标的关系，详见社区文档
- `from jqlib.technical_analysis import *` 不要拼错成 `from jqlib.alpha101 import *`（常见 AI 编错）

---

## jqfactor 因子数据库

与 jqlib 密切相关的因子数据获取函数（注意：这些来自 `jqfactor` 包，不是 `jqlib`）。

### get_all_factors

```python
from jqfactor import get_all_factors
print(get_all_factors())
# 返回 DataFrame：因子代码、因子名称、因子分类
```

### get_factor_values ★

```python
from jqfactor import get_factor_values

factor_data = get_factor_values(
    securities=['000001.XSHE'],
    factors=['Skewness60'],
    start_date='2017-01-01',
    end_date='2017-03-04'
)
```

**参数**：
- `securities`：股票池（字符串或列表）
- `factors`：因子名称（字符串或列表）
- `start_date`：开始日期（与 `count` 二选一）
- `end_date`：结束日期
- `count`：截止 `end_date` 之前的交易日数量（与 `start_date` 二选一）

**返回**：`dict`，key 为因子名称，value 为 `DataFrame`（index=日期, columns=股票代码）

**限制**：每次请求 因子数 × 股票数 × 交易日数 ≤ 200000

### get_factor_kanban_values

```python
from jqfactor import get_factor_kanban_values

df = get_factor_kanban_values(
    universe='hs300',
    bt_cycle='month_3',
    model='long_only',
    category=['quality', 'basics', 'emotion', 'growth', 'risk', 'pershare'],
    skip_paused=False,
    commision_slippage=0
)
```

---

## 常见失败模式

❌ `from jqlib import alpha101` → 正确写法是 `from jqlib.alpha101 import *`
❌ 混淆 Alpha101 和 Alpha191 的参数顺序
❌ 在 `get_factor_values` 中请求量超过 200000 限额
❌ `from jqfactor import alpha101` → `alpha101` 在 `jqlib` 里，不在 `jqfactor` 里
