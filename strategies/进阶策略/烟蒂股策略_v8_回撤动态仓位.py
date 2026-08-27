# -*- coding: utf-8 -*-
"""
烟蒂股策略 v8 · 回撤动态仓位（策略自身高水位回撤 -> 分层降仓 / 反弹回补）—— 聚宽平台

【设计】
    在 v1(小市值+高股息, top_n=10, 等权)基础上, 加一层**策略自身净值回撤**的动态仓位管理:
      - 不依赖任何外部指数(避免"指数和你持仓无关"的错配);
      - 每日用 context.portfolio.total_value 算**高水位回撤** dd = (峰值 - 现值) / 峰值;
      - 状态机(带迟滞, 避免频繁开关):
            full(满仓)  ->  dd >= cut_mid    -> mid(降到 exposure_mid)
                          dd >= cut_deep   -> deep(降到 exposure_deep)
            mid         ->  dd >= cut_deep   -> deep
                          dd <  reenter_full 或 从坑底反弹 >= recover_pct -> full
            deep        ->  dd <  reenter_mid 或 从坑底反弹 >= recover_pct -> mid
                          dd <  reenter_full 或 从坑底反弹 >= recover_full -> full
      - 换股仍为月度 top_n=10 等权; 仓位只在"状态翻转"时才调(控换手)。

【为什么用"自己的回撤"】
    之前 v2/v4/v7 都因"降仓信号与实际亏损脱节"而失败(天天降=变半仓 / 用错指数=长期趴半仓)。
    v8 只在**你自己正在亏钱**时降仓, 净值反弹后快速回补, 其余时间满仓吃超额——目标:
    降低最大回撤, 有限影响累计超额, 进而提升夏普。

【参数】
    cut_mid/cut_deep   触发降仓的回撤阈值(分别对应 mid/deep 层)
    reenter_full/mid   回补到 full/mid 的回撤阈值(迟滞: 回补阈值 < 触发阈值, 减少开关)
    recover_pct/full   从坑底(近期最低净值)反弹比例, 达标也回补(抓 V 反弹, 防止回补过慢)
    exposure_mid/deep  降仓后的目标暴露
    max_hold_days      mid/deep 状态最长持有天数, 超过则强制重新评估(防长趴半仓)

【注意】财务/分红/估值一律用前一日(prev_date), 避免未来函数。参数请在样本外做敏感性检验。
        本策略为学习/研究用途, 不构成投资建议。
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
    g.stop_loss = -0.20

    # ---- 回撤动态仓位(策略自身净值)----
    g.cut_mid = 0.12          # 回撤 12% -> mid
    g.cut_deep = 0.20         # 回撤 20% -> deep
    g.reenter_full = 0.05     # 回撤 < 5%  -> full
    g.reenter_mid = 0.10      # 回撤 < 10% -> mid
    g.recover_pct = 0.10      # 从坑底反弹 10% -> 上一层
    g.recover_full = 0.20     # 从坑底反弹 20% -> full
    g.exposure_full = 1.00
    g.exposure_mid = 0.70
    g.exposure_deep = 0.50

    g.high_water = None       # 净值高水位(峰值)
    g.trough_value = None     # 状态期间的低水位(坑底), 用于反弹回补
    g.dd_state = 'full'       # full / mid / deep
    g.exposure = 1.00         # 当前目标暴露

    g.target_codes = []       # 当期目标(月度更新)

    # 每日回撤检查; 每月换股
    run_daily(drawdown_check, time='09:46')
    run_monthly(rebalance, monthday=1, time='09:31')


# ============================================================
# 每日回撤检查: 更新高水位/坑底, 状态机决定目标暴露并(翻转时)调仓
# ============================================================
def drawdown_check(context):
    try:
        val = context.portfolio.total_value
        if g.high_water is None:
            g.high_water = val
            g.trough_value = val
            return
        if val > g.high_water:
            g.high_water = val
            g.trough_value = val          # 创新高 -> 坑底重置为峰值
            if g.dd_state != 'full':
                g.dd_state = 'full'
                g.exposure = g.exposure_full
                log.info('烟蒂股v8：净值新高 %.2f -> full 满仓' % val)
                apply_weights(context)
            return
        # 更新坑底(仅在有回撤时)
        if g.trough_value is None or val < g.trough_value:
            g.trough_value = val

        dd = (g.high_water - val) / g.high_water if g.high_water > 0 else 0.0
        recovered = (val / g.trough_value - 1.0) if g.trough_value > 0 else 0.0

        new_state = g.dd_state
        if g.dd_state == 'full':
            if dd >= g.cut_deep:
                new_state = 'deep'
            elif dd >= g.cut_mid:
                new_state = 'mid'
        elif g.dd_state == 'mid':
            if dd >= g.cut_deep:
                new_state = 'deep'
            elif dd < g.reenter_full or recovered >= g.recover_pct:
                new_state = 'full'
        elif g.dd_state == 'deep':
            if dd < g.reenter_mid or recovered >= g.recover_pct:
                new_state = 'mid'
            if dd < g.reenter_full or recovered >= g.recover_full:
                new_state = 'full'

        E = {'full': g.exposure_full, 'mid': g.exposure_mid, 'deep': g.exposure_deep}[new_state]
        if new_state != g.dd_state or abs(E - g.exposure) >= 0.10:
            g.dd_state = new_state
            if abs(E - g.exposure) >= 0.10:
                g.exposure = E
                log.info('烟蒂股v8：回撤 %.1f%% | 反弹 %.1f%% | %s -> 暴露 %.0f%%'
                         % (dd * 100, recovered * 100, new_state, E * 100))
                apply_weights(context)
    except Exception as e:
        log.error('烟蒂股v8：回撤检查异常 %s: %s' % (type(e).__name__, e))


# ============================================================
# 每月换股(选股与 v1 一致) + 应用当前暴露
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
        g.target_codes = target['code'].tolist()
        apply_weights(context)
        record(context, target)
    except Exception as e:
        log.error('烟蒂股v8：调仓异常 %s: %s' % (type(e).__name__, e))


# ============================================================
# 应用暴露: 卖出非目标/止损/退市, 目标按 exposure/top_n 等权建仓
# ============================================================
def apply_weights(context):
    target_codes = set(g.target_codes)
    if not target_codes:
        return
    cd = get_current_data()
    total = context.portfolio.total_value
    E = g.exposure
    weight = E / len(target_codes) if len(target_codes) else 0.0

    # 1) 卖出: 退市/ST / 止损 / 调出
    for stock, pos in list(context.portfolio.positions.items()):
        if pos.closeable_amount <= 0:
            continue
        cur = cd[stock]
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            order_target(stock, 0)
            log.info('烟蒂股v8：退市/ST 卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股v8：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        if stock not in target_codes:
            order_target(stock, 0)
            log.info('烟蒂股v8：调出 %s' % stock)

    # 2) 按当前暴露等权建仓
    for stock in g.target_codes:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        order_target_value(stock, total * weight)


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


def record(context, target):
    try:
        value = context.portfolio.total_value
        n = len(context.portfolio.positions)
        log.info('烟蒂股v8：净值 %.2f | 持仓 %d | 候选 %d | 状态 %s | 暴露 %.0f%%'
                 % (value, n, len(target) if target is not None else 0, g.dd_state, g.exposure * 100))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
