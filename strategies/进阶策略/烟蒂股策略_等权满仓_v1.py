# -*- coding: utf-8 -*-
"""
烟蒂股策略 · 等权满仓版（v1）—— 聚宽平台

【说明】这是"小市值 + 高股息可持续"代理口径的**等权满仓**版本（无凯莉、无动态降仓）。
    与 v2/v3（分级凯莉动态仓位 + 回撤保护）对照，用于同区间 A/B 对比：
      - v1：等权 top_n、满仓（收益高、波动/回撤大）
      - v3：等权 top_n + 分级凯莉温和降仓 + 回撤保护（回撤低、收益较稳）

【选股口径】
    全市场 -> 剔除 ST/*ST/退市、科创板(688)、北交所(4/8/920)、次新(<365天)、停牌
    -> 取市值最小 pool_size 只 -> 近一年分红/市值 -> 剔除支付率异常、市净率<=0
    -> 股息率降序取 top_n -> **等权、满仓**。

【使用】复制到聚宽在线编辑器回测。
【注意】本策略为量化学习/研究用途，不构成投资建议。
"""

from jqdata import *
import pandas as pd
import datetime


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)

    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(PriceRelatedSlippage(0.00246))

    g.pool_size = 1000        # 市值最小的 N 只（候选池）
    g.top_n = 10              # 持有数量（等权、满仓）
    g.min_hold = 5            # 严格候选低于此数时放宽支付率上限兜底
    g.payout_max = 1.0        # 支付率上限（分红<=净利润，可持续）
    g.payout_relax_max = 2.0  # 兜底时支付率上限
    g.max_div_yield = 0.40    # 股息率上限（避免特别分红/股价崩塌）
    g.min_circ_mcap = 1.0     # 最小流通市值（亿元）
    g.min_list_days = 365     # 次新剔除
    g.stop_loss = -0.20       # 相对成本止损

    run_monthly(rebalance, monthday=1, time='09:31')


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
        manage_holdings(context, target)
        record(context, target)
    except Exception as e:
        log.error('烟蒂股：调仓异常 %s: %s' % (type(e).__name__, e))


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
    has_profit_pb = (df['payout_rate'] > 0) & (df['pb_ratio'] > 0)
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


def manage_holdings(context, target):
    target_codes = set(target['code'].tolist())
    cd = get_current_data()
    for stock, pos in list(context.portfolio.positions.items()):
        if pos.closeable_amount <= 0:
            continue
        cur = cd[stock]
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            order_target(stock, 0)
            log.info('烟蒂股：退市/ST 卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        if stock not in target_codes:
            order_target(stock, 0)
            log.info('烟蒂股：调出 %s' % stock)

    codes = target['code'].tolist()
    if not codes:
        return
    weight = 1.0 / len(codes)  # 等权、满仓
    for stock in codes:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        order_target_value(stock, context.portfolio.total_value * weight)


def record(context, target):
    try:
        value = context.portfolio.total_value
        n = len(context.portfolio.positions)
        log.info('烟蒂股：净值 %.2f | 持仓 %d | 候选 %d' % (value, n, len(target)))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
