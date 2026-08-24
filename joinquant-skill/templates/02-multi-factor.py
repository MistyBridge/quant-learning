# -*- coding: utf-8 -*-
"""
02 — 多因子选股策略
适用场景：月度调仓，从指数成分股中按 PE/市值/动量 多因子打分选股。
使用方法：修改 INDEX, HOLD_NUM, 因子权重后粘贴到聚宽运行。
"""

from jqdata import *
from jqfactor import get_factor_values


INDEX = '000300.XSHG'   # ← 股票池来源（沪深300）
HOLD_NUM = 10            # ← 持仓股票数量


def initialize(context):
    set_benchmark(INDEX)
    set_option('use_real_price', True)

    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(PriceRelatedSlippage(0.00246))

    run_monthly(rebalance, monthday=1, time='09:31')


def rebalance(context):
    date = context.current_dt.strftime('%Y-%m-%d')
    stocks = get_index_stocks(INDEX, date)
    stocks = filter_paused_and_st(stocks, date)

    if len(stocks) == 0:
        return

    scored = score_stocks(stocks, date)
    target = scored.nlargest(HOLD_NUM).index.tolist()

    for s in context.portfolio.positions:
        if s not in target:
            order_target(s, 0)
            log.info('调出 %s' % s)

    weight = 1.0 / HOLD_NUM
    for s in target:
        order_target_value(s, context.portfolio.total_value * weight)


def score_stocks(stocks, date):
    """多因子综合打分：PE倒数（低估值）+ 小市值 + 动量"""
    import pandas as pd

    factors = get_factor_values(
        securities=stocks,
        factors=['pe_ratio', 'market_cap'],
        end_date=date,
        count=1,
    )

    pe = factors['pe_ratio'].iloc[0]
    mcap = factors['market_cap'].iloc[0]

    pe_score = (1.0 / pe.clip(lower=1)).rank(pct=True)
    mcap_score = (-mcap).rank(pct=True)

    prices = get_price(
        stocks, end_date=date, count=20,
        fields=['close'], panel=False
    )
    mom = prices.groupby('code')['close'].apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)
    mom_score = mom.rank(pct=True)

    combined = pe_score * 0.4 + mcap_score * 0.3 + mom_score * 0.3
    return combined.dropna()


def filter_paused_and_st(stocks, date):
    """过滤停牌和 ST 股票"""
    current = get_current_data()
    return [s for s in stocks
            if not current[s].paused
            and not current[s].is_st
            and 'ST' not in current[s].name
            and '*' not in current[s].name]
