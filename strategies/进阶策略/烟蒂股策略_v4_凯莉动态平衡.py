# -*- coding: utf-8 -*-
"""
烟蒂股策略 v4 · 凯莉动态平衡系统 —— 聚宽平台

【设计】在"小市值+高股息"选股基础上,加一套**凯莉仓位 + 风控 + 高频再平衡**联动系统:
    1) 风险暴露上限 E——用「凯莉边缘 / 波动率目标 / 回撤」三者取更保守,风险期自动收缩仓位(可低到 min_exposure):
         E = min( 1/2凯莉 × (年化收益-无风险)/波动² , vol_target / 现实波动 )  [再夹到 min/max]
         且 自高点回撤 > dd_guard 时强制降到 min_exposure。
    2) 凯莉倾斜权重——在当期烟蒂股内按 股息率/(PB+0.5) 打分,高确定性多给一点,单票封顶,总和=E。
    3) 带内高频再平衡——每周调仓,但只对"偏离目标权重超过 rebalance_band"的仓位动手(否则不动),
       以放大换手(卖高买低/落袋)又控制成本;换仓/止损/退市照常。

【与 v1/v2/v3】选股口径一致;本版"换手更高、风险暴露受控",是"放大换手 + 尽可能减少风险暴露"的实验版。

【注意】换手越高、交易成本越大;每周多次 get_fundamentals/finance.run_query 也会更慢。本策略为学习/研究用途，不构成投资建议。
"""

from jqdata import *
import pandas as pd
import numpy as np
import datetime
import collections


# ============================================================
# 初始化
# ============================================================
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)

    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(PriceRelatedSlippage(0.00246))

    # ---- 选股(与 v1 一致)----
    g.pool_size = 1000
    g.top_n = 10
    g.min_hold = 5
    g.payout_max = 1.0
    g.payout_relax_max = 2.0
    g.max_div_yield = 0.40
    g.min_circ_mcap = 1.0
    g.payout_min = 0.0
    g.min_list_days = 365
    g.stop_loss = -0.18

    # ---- 风险暴露上限(凯莉 + 波动率目标 + 回撤)----
    g.kelly_mult = 0.50        # 1/2 凯莉
    g.kelly_window = 60        # 回看交易日
    g.rf = 0.03                # 无风险利率
    g.vol_target = 0.20        # 年化波动率目标
    g.min_exposure = 0.40      # 最低暴露
    g.max_exposure = 1.00      # 最高暴露
    g.default_exposure = 0.80  # 数据不足时
    g.dd_guard = -0.25         # 回撤超过 25% 强制降到最低仓

    # ---- 权重倾斜(给定"暴露给谁")----
    g.tilt_min = 0.5
    g.tilt_max = 2.0
    g.max_pos_weight = 0.15    # 单票上限(10 只, 平均 10%)

    # ---- 高频再平衡 ----
    g.rebalance_band = 0.03    # 漂移带: 偏离目标权重超过此幅度才调仓

    g.recent_pv = collections.deque(maxlen=g.kelly_window + 10)

    run_daily(track_value, time='14:55')
    run_weekly(rebalance, weekday=1, time='09:31')


def track_value(context):
    g.recent_pv.append(context.portfolio.total_value)


# ============================================================
# 风险暴露上限 E (凯莉 + 波动率目标 + 回撤保护)
# ============================================================
def target_exposure(context):
    pv = list(g.recent_pv)
    if len(pv) < 30:
        return g.default_exposure
    r = np.diff(pv) / np.asarray(pv[:-1], dtype=float)
    mu = r.mean() * 250
    sd = r.std() * np.sqrt(250)
    if sd < 1e-6:
        return g.max_exposure

    # 凯莉暴露
    kelly_exp = g.kelly_mult * max(0.0, (mu - g.rf) / (sd ** 2))
    kelly_exp = float(min(g.max_exposure, max(g.min_exposure, kelly_exp)))
    # 波动率目标暴露: 波动越大暴露越小
    vol_exp = float(min(g.max_exposure, max(g.min_exposure, g.vol_target / sd)))
    # 取更保守
    exp = min(kelly_exp, vol_exp)

    # 回撤保护
    peak = max(g.recent_pv)
    cur = context.portfolio.total_value
    if peak > 0:
        dd = cur / peak - 1.0
        if dd < g.dd_guard:
            exp = g.min_exposure
            log.info('烟蒂股v4：回撤 %.1f%% 触发保护 -> 最低仓 %.0f%%' % (dd * 100, g.min_exposure * 100))

    return float(min(g.max_exposure, max(g.min_exposure, exp)))


# ============================================================
# 每月/每周调仓入口
# ============================================================
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

        E = target_exposure(context)
        log.info('烟蒂股v4：目标暴露 %.0f%%' % (E * 100))
        weights = compute_weights(target, E)
        apply_weights(context, weights, E)
        record(context, target, E)
    except Exception as e:
        log.error('烟蒂股v4：调仓异常 %s: %s' % (type(e).__name__, e))


# ============================================================
# 选股(与 v1 一致)
# ============================================================
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


# ============================================================
# 凯莉倾斜权重: 高确定性多给, 单票封顶, 总和 = E
# ============================================================
def compute_weights(target, E):
    df = target.copy()
    n = len(df)
    if n == 0:
        return []
    score = df['div_yield'].clip(lower=1e-6) / (df['pb_ratio'] + 0.5)
    rel = score / (score.mean() if score.mean() > 0 else 1.0)
    rel = rel.clip(g.tilt_min, g.tilt_max)
    tilt = rel / rel.sum()          # 归一化, 总和=1
    w = (E * tilt).clip(upper=g.max_pos_weight)
    if w.sum() > 0:
        w = w * (E / w.sum())       # 重新归一化到 E
        w = w.clip(upper=g.max_pos_weight)
    return list(zip(df['code'].tolist(), w.tolist()))


# ============================================================
# 带内高频再平衡: 只有偏离目标权重超过 rebalance_band 才动
# ============================================================
def apply_weights(context, weights, E):
    target_map = dict(weights)
    cd = get_current_data()
    total = context.portfolio.total_value
    positions = context.portfolio.positions

    # 1) 卖出: 退市/ST / 止损 / 调出
    for stock, pos in list(positions.items()):
        if pos.closeable_amount <= 0:
            continue
        cur = cd[stock]
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            order_target(stock, 0)
            log.info('烟蒂股v4：退市/ST 卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股v4：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        if stock not in target_map:
            order_target(stock, 0)
            log.info('烟蒂股v4：调出 %s' % stock)

    # 2) 带内再平衡: 只对偏离目标权重超 band 的仓位动手
    for stock, w in weights:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        if stock in positions and positions[stock].value > 0:
            cur_w = positions[stock].value / total if total > 0 else 0.0
            if abs(cur_w - w) < g.rebalance_band:
                continue    # 在带内, 不动
        order_target_value(stock, total * w)


def record(context, target, E):
    try:
        value = context.portfolio.total_value
        n = len(context.portfolio.positions)
        log.info('烟蒂股v4：净值 %.2f | 持仓 %d | 候选 %d | 暴露 %.0f%%'
                 % (value, n, len(target), E * 100))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
