# -*- coding: utf-8 -*-
"""
01 — 单股票均线策略（Hello World）
适用场景：入门级，单只股票，5/20 日均线交叉。
使用方法：修改 g.security 和均线参数后直接粘贴到聚宽编辑器运行。
"""


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)

    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(PriceRelatedSlippage(0.00246))

    g.security = '000001.XSHE'       # ← 改成你要交易的股票
    g.fast_period = 5                 # 短期均线天数
    g.slow_period = 20                # 长期均线天数

    run_daily(trade, time='09:31')


def trade(context):
    security = g.security
    close = attribute_history(security, g.slow_period + 1, '1d', ['close'])['close']

    ma_fast = close[-g.fast_period:].mean()
    ma_slow = close[-g.slow_period:].mean()

    if ma_fast > ma_slow and security not in context.portfolio.positions:
        order_value(security, context.portfolio.available_cash * 0.95)
        log.info('金叉买入 %s' % security)

    elif ma_fast < ma_slow and security in context.portfolio.positions:
        pos = context.portfolio.positions[security]
        if pos.closeable_amount > 0:
            order_target(security, 0)
            log.info('死叉卖出 %s' % security)
