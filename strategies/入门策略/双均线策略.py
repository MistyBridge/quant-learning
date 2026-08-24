"""
双均线策略 - 聚宽平台
策略逻辑：基于5日/20日均线金叉死叉的趋势跟踪策略
- 金叉（短均线上穿长均线）-> 买入
- 死叉（短均线下穿长均线）-> 卖出

使用方式：复制到聚宽在线编辑器中运行回测
"""

# ============================================================
# 初始化函数，整个回测只在开始时运行一次
# ============================================================
def initialize(context):
    # 设置交易标的：沪深300成分股中的平安银行
    g.security = '000001.XSHE'

    # 均线参数
    g.short_period = 5    # 短期均线天数
    g.long_period = 20    # 长期均线天数

    # 设置基准：沪深300
    set_benchmark('000300.XSHG')

    # 开启动态复权
    set_option('use_real_price', True)

    # 设置交易时间
    run_daily(market_open, time='9:30')


# ============================================================
# 每日开盘时运行的交易逻辑
# ============================================================
def market_open(context):
    security = g.security

    # 获取历史数据：需要 long_period + 1 天的数据来计算均线
    df = attribute_history(security, g.long_period + 1, '1d', ['close'])

    # 计算短期和长期均线
    short_ma = df['close'][-g.short_period:].mean()
    long_ma = df['close'][-g.long_period:].mean()

    # 计算前一天的均线（用于判断金叉/死叉）
    short_ma_prev = df['close'][-(g.short_period + 1):-1].mean()
    long_ma_prev = df['close'][-(g.long_period + 1):-1].mean()

    # 获取当前持仓
    current_position = context.portfolio.positions.get(security)

    # ------ 交易逻辑 ------

    # 金叉：短均线从下方上穿长均线 -> 买入
    if short_ma_prev <= long_ma_prev and short_ma > long_ma:
        if current_position is None or current_position.total_amount == 0:
            # 全仓买入
            order_target_value(security, context.portfolio.total_value)
            log.info(f"【买入】{security} | 短MA={short_ma:.2f} > 长MA={long_ma:.2f}")

    # 死叉：短均线从上方下穿长均线 -> 卖出
    elif short_ma_prev >= long_ma_prev and short_ma < long_ma:
        if current_position is not None and current_position.total_amount > 0:
            # 全仓卖出
            order_target(security, 0)
            log.info(f"【卖出】{security} | 短MA={short_ma:.2f} < 长MA={long_ma:.2f}")


# ============================================================
# 收盘后运行（可选，用于记录每日状态）
# ============================================================
def after_market_close(context):
    positions = context.portfolio.positions
    if positions:
        for stock, pos in positions.items():
            log.info(f"持仓: {stock}, 数量: {pos.total_amount}, 市值: {pos.value:.2f}")
    else:
        log.info("当前无持仓")
