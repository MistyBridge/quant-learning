# -*- coding: utf-8 -*-
"""
04 — 截面动量选股策略
适用场景：周度调仓，从全 A 股中选近期涨幅最大的 N 只持有。
使用方法：修改 UNIVERSE, HOLD_NUM, LOOKBACK 后粘贴到聚宽运行。
"""

from jqdata import *


UNIVERSE = '000905.XSHG'  # ← 股票池来源（中证500）
HOLD_NUM = 20              # ← 持仓数量
LOOKBACK = 20              # ← 动量回看天数
MIN_MARKET_CAP = 30        # ← 最低市值（亿元），过滤壳股


def initialize(context):
    set_benchmark(UNIVERSE)
    set_option('use_real_price', True)

    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(PriceRelatedSlippage(0.00246))

    run_weekly(rebalance, weekday=1, time='09:31')


def rebalance(context):
    date = context.current_dt.strftime('%Y-%m-%d')
    stocks = get_index_stocks(UNIVERSE, date)
    stocks = filter_stocks(stocks)

    if len(stocks) < HOLD_NUM:
        return

    momentum = calc_momentum(stocks)
    target = momentum.nlargest(HOLD_NUM).index.tolist()

    for s in list(context.portfolio.positions.keys()):
        if s not in target:
            order_target(s, 0)

    weight = 1.0 / HOLD_NUM
    for s in target:
        order_target_value(s, context.portfolio.total_value * weight)


def calc_momentum(stocks):
    """计算截面动量：过去 LOOKBACK 天收益率"""
    import pandas as pd

    prices = get_price(
        stocks, count=LOOKBACK + 1, end_date=None,
        fields=['close'], panel=False,
    )
    ret = prices.groupby('code')['close'].apply(
        lambda x: x.iloc[-1] / x.iloc[0] - 1 if len(x) > 1 else 0
    )
    return ret


def filter_stocks(stocks):
    """过滤停牌、ST、涨跌停、低市值股票"""
    current = get_current_data()
    result = []
    for s in stocks:
        d = current[s]
        if d.paused:
            continue
        if d.is_st or 'ST' in d.name or '*' in d.name:
            continue
        if d.day_open == d.high_limit or d.day_open == d.low_limit:
            continue
        result.append(s)
    return result
