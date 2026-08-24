# -*- coding: utf-8 -*-
"""
烟蒂股策略 v2 · 正向凯莉 —— 聚宽平台

【与 v1 的差异】选股口径与 v1(原版/等权满仓)完全一致,只把"总仓位"改为**正向分级凯莉**:
    用组合近 kelly_window 日收益的年化均值/波动算 Kelly,取 kelly_mult×max(0,Kelly),
    映射到**权益暴露**(介于 min_exposure~max_exposure);行情好接近满仓,转弱自动降仓留现金。
    候选内为**等权**(每只 = exposure/top_n),与 v1 的唯一区别就是"总仓位暴露"。

【A/B】v1 等权满仓 / v2 正向凯莉 / v3 逆向凯莉 —— 三者选股完全相同,只差仓位管理。

【注意】本策略为量化学习/研究用途,不构成投资建议。
"""

from jqdata import *
import pandas as pd
import numpy as np
import datetime
import collections


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)

    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(PriceRelatedSlippage(0.00246))

    # ---- 与 v1 相同的选股参数 ----
    g.pool_size = 1000        # 市值最小的 N 只（候选池）
    g.top_n = 10              # 持有数量（股息率降序）
    g.min_hold = 5            # 严格候选低于此数时放宽支付率上限兜底
    g.payout_relax_max = 2.0  # 兜底时支付率上限
    g.max_div_yield = 0.40    # 股息率上限
    g.min_circ_mcap = 1.0     # 最小流通市值（亿元）
    g.payout_min = 0.0        # 股利支付率下限
    g.payout_max = 1.0        # 股利支付率上限
    g.min_list_days = 365     # 次新剔除
    g.stop_loss = -0.20       # 相对成本止损

    # ---- 正向凯莉 ----
    g.kelly_mult = 0.5        # 分数凯莉（1/2 凯莉）
    g.kelly_window = 60       # 回看交易日数
    g.min_exposure = 0.5      # 权益暴露下限
    g.max_exposure = 1.0      # 权益暴露上限
    g.default_exposure = 1.0  # 数据不足时初始仓位
    g.rf = 0.03               # 无风险利率

    g.recent_pv = collections.deque(maxlen=g.kelly_window + 5)

    run_daily(track_value, time='14:55')
    run_monthly(rebalance, monthday=1, time='09:31')


def track_value(context):
    g.recent_pv.append(context.portfolio.total_value)


def kelly_exposure(context):
    pv = list(g.recent_pv)
    if len(pv) < 60:
        return g.default_exposure
    r = np.diff(pv) / np.asarray(pv[:-1], dtype=float)
    mu = r.mean() * 250
    sd = r.std() * np.sqrt(250)
    if sd < 1e-6:
        return g.max_exposure
    kelly = (mu - g.rf) / (sd ** 2)
    frac = g.kelly_mult * max(0.0, kelly)
    return float(min(g.max_exposure, max(g.min_exposure, frac)))


def rebalance(context):
    date = context.current_dt.date()
    prev = context.previous_date
    try:
        universe = get_universe(context, prev, date)
        if not universe:
            return
        pool = get_small_cap_pool(universe, prev)
        if not pool:
            return
        target = screen_cigar_butt(pool, prev, date)
        if target is None or len(target) == 0:
            return
        exposure = kelly_exposure(context)
        log.info('烟蒂股v2(正向凯莉)：仓位暴露 %.0f%%' % (exposure * 100))
        manage_holdings(context, target, exposure)
        record(context, target, exposure)
    except Exception as e:
        log.error('烟蒂股v2：调仓异常 %s: %s' % (type(e).__name__, e))


def get_universe(context, prev, date):
    all_sec = get_all_securities(types=['stock'], date=date)
    if all_sec is None or len(all_sec) == 0:
        return []
    cd = get_current_data()
    kept = []
    for code in all_sec.index:
        if code[0] in ('4', '8') or code[:2] == '68' or code[:3] == '920':
            continue
        info = all_sec.loc[code]
        try:
            if (date - info['start_date']).days < g.min_list_days:
                continue
        except Exception:
            pass
        cur = cd[code]
        if cur.paused:
            continue
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            continue
        kept.append(code)
    return kept


def get_small_cap_pool(universe, prev):
    q = query(valuation.code).filter(
        valuation.code.in_(universe)
    ).order_by(valuation.market_cap.asc()).limit(g.pool_size)
    df = get_fundamentals(q, date=prev)
    if df is None or len(df) == 0:
        return []
    return df['code'].tolist()


def screen_cigar_butt(pool, prev, date):
    if not pool:
        return pd.DataFrame()
    time0 = prev - datetime.timedelta(days=365)
    f = finance.STK_XR_XD
    q = query(
        f.code, f.bonus_ratio_rmb, f.total_capital_before_transfer, f.a_registration_date
    ).filter(f.code.in_(pool), f.a_registration_date >= time0, f.a_registration_date <= prev)
    dd = finance.run_query(q)
    if dd is None or len(dd) == 0:
        return pd.DataFrame()
    dd = dd.fillna(0)
    dd['cash_div'] = (dd['bonus_ratio_rmb'] / 10) * dd['total_capital_before_transfer'] * 1e4
    div = dd.groupby('code')['cash_div'].sum()

    q2 = query(
        valuation.code, valuation.market_cap, valuation.circulating_market_cap,
        valuation.pe_ratio, valuation.pb_ratio,
    ).filter(valuation.code.in_(div.index))
    fund = get_fundamentals(q2, date=prev)
    if fund is None or len(fund) == 0:
        return pd.DataFrame()
    cap = fund.set_index('code')

    df = pd.concat([div, cap], axis=1, sort=False).reset_index()
    df['cash_div'] = df['cash_div'] / 1e8
    df['div_yield'] = df['cash_div'] / df['market_cap']
    df['net_profit'] = df['market_cap'] / df['pe_ratio']
    df['payout_rate'] = df['cash_div'] / df['net_profit']

    df = df.dropna(subset=['div_yield', 'payout_rate', 'pb_ratio', 'market_cap'])
    has_profit_pb = (df['payout_rate'] > g.payout_min) & (df['pb_ratio'] > 0)
    if 'circulating_market_cap' in df.columns:
        has_profit_pb = has_profit_pb & (df['circulating_market_cap'] >= g.min_circ_mcap)
    has_sane_yield = df['div_yield'] <= g.max_div_yield

    strict = df[has_profit_pb & has_sane_yield & (df['payout_rate'] <= g.payout_max)]
    if len(strict) < g.min_hold:
        fuzzy = df[has_profit_pb & has_sane_yield & (df['payout_rate'] <= g.payout_relax_max)]
        sel = fuzzy
    else:
        sel = strict

    top = sel.sort_values('div_yield', ascending=False).head(g.top_n)
    return top.reset_index(drop=True)


def manage_holdings(context, target, exposure):
    target_codes = set(target['code'].tolist())
    cd = get_current_data()
    for stock, pos in list(context.portfolio.positions.items()):
        if pos.closeable_amount <= 0:
            continue
        cur = cd[stock]
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            order_target(stock, 0)
            log.info('烟蒂股v2：退市/ST 卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股v2：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        if stock not in target_codes:
            order_target(stock, 0)
            log.info('烟蒂股v2：调出 %s' % stock)

    codes = target['code'].tolist()
    if not codes:
        return
    weight = exposure / len(codes)   # 等权 × 暴露；其余留现金
    for stock in codes:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        order_target_value(stock, context.portfolio.total_value * weight)


def record(context, target, exposure):
    try:
        value = context.portfolio.total_value
        n = len(context.portfolio.positions)
        log.info('烟蒂股v2：净值 %.2f | 持仓 %d | 候选 %d | 暴露 %.0f%%'
                 % (value, n, len(target), exposure * 100))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
