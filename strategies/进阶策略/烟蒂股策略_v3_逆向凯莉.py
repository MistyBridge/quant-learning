# -*- coding: utf-8 -*-
"""
烟蒂股策略 v3 · 逆向凯莉 —— 聚宽平台

【与 v1 的差异】选股口径与 v1(原版/等权满仓)完全一致,只把"总仓位"改为**逆向/均值回归式凯莉**:
    以"组合最近低点"为基准做逆向加减仓:
      - 越跌越加仓：组合回落、越接近/跌破最近低点 -> 仓位升到 100%（最低仓以上）；
      - 涨超低点减仓：现价高于最近低点 X% 时按比例减仓；涨超 reduce_trigger(默认 20%) -> 减到最低仓；
      - 最低仓位：永不低于 min_position(默认 50%)。
    候选内为**等权**(每只 = exposure/top_n),与 v1 的唯一区别就是"仓位随最近低点逆向调整"。

【应用时点】与 v1 **完全相同的买卖节奏**（每月对当期目标全部票做一次 `order_target_value`），
    只是把目标权重从"等权"换成"逆向凯莉权重"（exposure/len）。因此**买卖笔数与盈亏次数应与 v1 一致**，仅仓位大小不同。

【A/B】v1 等权满仓 / v2 正向凯莉 / v3 逆向凯莉 —— 三者选股完全相同,只差仓位管理。

【注意】"越跌越加仓"属逆向抄底,可能在下跌中放大暴露(放大回撤),请结合自身风险偏好；本策略为学习/研究用途，不构成投资建议。
"""

from jqdata import *
import pandas as pd
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

    # ---- 逆向凯莉（越跌越加仓 / 涨超低点减仓）----
    g.min_position = 0.50     # 最低仓位（始终 >= 50%）
    g.max_position = 1.00     # 最高仓位
    g.default_position = 1.00 # 数据不足时初始仓位
    g.trough_window = 120     # "最近低点"回看交易日数
    g.reduce_trigger = 0.20   # 现价高于最近低点 20% 时减至最低仓（0~20% 线性递减）

    g.recent_pv = collections.deque(maxlen=g.trough_window + 10)

    run_daily(track_value, time='14:55')
    run_monthly(rebalance, monthday=1, time='09:31')


def track_value(context):
    g.recent_pv.append(context.portfolio.total_value)


def trough_exposure(context):
    pv = list(g.recent_pv)
    if len(pv) < 30:
        return g.default_position
    low = min(pv)
    if low <= 0:
        return g.max_position
    cur = context.portfolio.total_value
    rebound = max(0.0, cur / low - 1.0)
    exp = g.max_position - ((g.max_position - g.min_position) / g.reduce_trigger) * rebound
    exp = float(min(g.max_position, max(g.min_position, exp)))
    log.info('烟蒂股v3(逆向凯莉)：低点 %.2f | 现价 %.2f | 反弹 %.1f%% -> 仓位 %.0f%%'
             % (low, cur, rebound * 100, exp * 100))
    return exp


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
        exposure = trough_exposure(context)
        manage_holdings(context, target, exposure)
        record(context, target, exposure)
    except Exception as e:
        log.error('烟蒂股v3：调仓异常 %s: %s' % (type(e).__name__, e))


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
            log.info('烟蒂股v3：退市/ST 卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股v3：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        if stock not in target_codes:
            order_target(stock, 0)
            log.info('烟蒂股v3：调出 %s' % stock)

    codes = target['code'].tolist()
    if not codes:
        return
    weight = exposure / len(codes)   # 逆向凯莉权重：作用于所有目标, 与 v1 同频(每月)调仓 -> 笔数/盈亏次数与 v1 一致, 仅仓位大小不同
    for stock in codes:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        order_target_value(stock, context.portfolio.total_value * weight)


def record(context, target, exposure):
    try:
        value = context.portfolio.total_value
        n = len(context.portfolio.positions)
        log.info('烟蒂股v3：净值 %.2f | 持仓 %d | 候选 %d | 暴露 %.0f%%'
                 % (value, n, len(target), exposure * 100))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
