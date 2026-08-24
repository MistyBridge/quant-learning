# 08 — 其他函数

> 画图、日志、文件读写、消息推送、代码转换、性能分析等辅助工具。

## record ★ 画图函数

```python
record(**kwargs)
```

回测/模拟专用。在回测图表上画出额外曲线（收益曲线和基准曲线是自动画的）。

**参数**：一个或多个 `key=value`，key 为曲线名称，value 为数值（不能是列表）

**注意**：
- 按天展示，分钟回测取当天最后一次 `record` 的值
- 以 16:00 为界，之后绘制的属于第二天
- 需从回测开始就调用，不支持中间时段开始调用

```python
def handle_data(context, data):
    d = data['000001.XSHE']
    record(price=d.price, open=d.open, close=d.close)
    record(price=100)  # 画一条值为100的直线
```

---

## log 日志

```python
log.error(content)
log.warn(content)
log.info(content)
log.debug(content)
print(content1, content2, ...)  # 等同于 log.info，但每个元素占一行
```

### log.set_level 设定日志级别

```python
log.set_level(name, level)
```

**name** 取值：
- `'order'`：order 系列 API 产生的日志
- `'history'`：history/attribute_history/get_price 产生的日志
- `'strategy'`：策略代码中的自定义日志
- `'system'`：系统日志

**level** 取值（级别递增）：`'debug'` < `'info'` < `'warning'` < `'error'`

```python
log.set_level('order', 'info')
```

建议保持默认 `debug` 级别，便于排查问题。

---

## send_message 发送微信消息

```python
send_message(message, channel='weixin')
```

**仅模拟交易可用**，回测中调用会被忽略。

**限制**：
- 需绑定并开启微信通知
- 每个账号每天最多 5 条自定义消息（可用积分兑换更多）
- 消息长度 ≤ 200 字符，不能包含回车/换行
- 与下单通知不同：下单通知每天最多 60 条，且需开启对应模拟交易的通知开关

```python
send_message('美好的一天~')
```

---

## write_file 写文件

```python
write_file(path, content, append=False)
```

将数据写入聚宽研究环境的私有空间。

**参数**：
- `path`：相对路径（相对于研究根目录）
- `content`：文件内容（str/unicode/二进制）
- `append`：追加模式，默认 `False`（清除原内容）

```python
write_file('test.txt', 'hello world')

import json
write_file('HS300.stocks.json', json.dumps(get_index_stocks('000300.XSHG')))

df = attribute_history('000001.XSHE', 5, '1d')
write_file('df.csv', df.to_csv(), append=False)
```

---

## read_file 读文件

```python
read_file(path)
```

读取研究环境中的私有文件。返回原始内容（bytes），不做 decode。

```python
import json
content = read_file('HS300.stocks.json')
securities = json.loads(content)

# Python 3
import pandas as pd
from io import BytesIO
body = read_file('open.csv')
data = pd.read_csv(BytesIO(body))
```

**注意**：不能读取本地文件，需先上传到聚宽研究环境。

---

## 自定义 Python 库

将 `.py` 文件放在研究根目录，策略中直接 `import`：

```python
# 研究根目录/mylib.py
from kuanke.user_space_api import *
my_stocks = get_index_stocks('000300.XSHG')

# 策略代码中
from mylib import *
def initialize(context):
    log.info(my_stocks)
```

暂时只支持根目录的 `.py` 文件，不支持子目录。

---

## normalize_code 代码转换

```python
normalize_code(code)
```

将其他格式的股票代码转为聚宽格式。支持 A 股、期货、场内基金。

```python
codes = ('000001', 'SZ000001', '000001SZ', '000001.sz', '000001.XSHE')
print(normalize_code(codes))
# ['000001.XSHE', '000001.XSHE', '000001.XSHE', '000001.XSHE', '000001.XSHE']
```

---

## enable_profile 性能分析

```python
enable_profile()
```

回测专用。在所有代码最上方调用，点击"运行回测"后在结果页看到性能分析。

**注意**：
- 本身会影响性能，不需要时不要调用
- 耗时长的回测建议先分析短周期（如一周）

---

## create_backtest 研究中创建回测

```python
create_backtest(
    algorithm_id, start_date, end_date,
    frequency='day', initial_cash=10000,
    initial_positions=None, extras=None,
    name=None, code='', benchmark=None,
    python_version=2, use_credit=False
)
```

只能在研究中使用。`extras` 中的值会在 `initialize` 执行后覆盖 `g` 变量。

---

## get_backtest 研究中获取回测信息

```python
gt = get_backtest(backtest_id)
gt.get_status()        # 回测状态
gt.get_params()        # 回测参数
gt.get_results()       # 收益曲线
gt.get_positions()     # 持仓详情
gt.get_orders()        # 交易详情
gt.get_records()       # record() 记录
gt.get_risk()          # 总风险指标
gt.get_period_risks()  # 分月风险指标
gt.get_balances()      # 每日市值
```

---

## 常见失败模式

❌ `record(price=[1,2,3])` → value 不能是列表，只能是单个数值
❌ 在回测中使用 `send_message` 期望收到微信 → 只在模拟交易生效
❌ `read_file('/home/user/data.csv')` → 只能读研究根目录的相对路径
❌ `log.set_level('all', 'info')` → name 必须是 `'order'`/`'history'`/`'strategy'`/`'system'`
