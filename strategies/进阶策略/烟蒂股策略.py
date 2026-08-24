# -*- coding: utf-8 -*-
"""
烟蒂股策略 v2 —— 小市值 + 高股息可持续 + 分级凯莉仓位 + 动态平衡 + 分散投资

【与 v1 的差异】
    1) 加大分散：top_n 10 -> 20，候选池 pool_size 1000 -> 1500，降低个体/小市值集中风险。
    2) 分级凯莉仓位分配：在当期烟蒂股内，按"股息率高、市净率低"做**有上限的 Kelly 倾斜权重**
       （高确定性给更高权重），单票设置上限 max_pos_weight，杜绝过度集中（分级 = 分层仓位）。
    3) 动态平衡（分级凯莉总体仓位）：用**组合近 kelly_window 个交易日收益的年化均值/波动**算 Kelly，
       取"分数凯莉"= kelly_mult × max(0, Kelly)，映射到**权益仓位暴露 exposure**（介于 min/max），
       行情好时接近满仓，回撤/波动放大时自动降仓，其余留现金。
    4) 最大回撤保护：组合自历史高点回撤超过 max_dd_deRisk 时，强制降到 min_exposure。

【选股口径】（与 v1 相同）
    全市场 -> 剔除 ST/*ST/退市、科创板(688)、北交所(4/8/920)、次新(<365天)、停牌
    -> 取市值最小 pool_size 只 -> 近一年分红/市值 -> 剔除支付率异常、市净率<=0
    -> 股息率降序取 top_n。

【使用】复制到聚宽在线编辑器回测。可调参数见 initialize（g.*）。
【注意】本策略为量化学习/研究用途，不构成投资建议。
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

    # ---------- 选股 ----------
    g.pool_size = 1500        # 市值最小的 N 只（候选池，加大）
    g.top_n = 20              # 持有数量（加大分散）
    g.min_hold = 8            # 严格候选低于此数时放宽支付率上限兜底
    g.payout_max = 1.0        # 支付率上限（分红<=净利润，可持续）
    g.payout_relax_max = 2.0  # 兜底时支付率上限
    g.max_div_yield = 0.40    # 股息率上限（避免特别分红/股价崩塌）
    g.min_circ_mcap = 1.0     # 最小流通市值（亿元）
    g.min_list_days = 365     # 次新剔除

    # ---------- 交易 / 风控 ----------
    g.stop_loss = -0.18       # 相对成本止损
    g.rf = 0.03               # 无风险利率（用于 Kelly）

    # ---------- 分级凯莉 · 动态仓位 ----------
    g.kelly_mult = 0.25       # 分数凯莉：取 1/4 凯莉
    g.kelly_window = 120      # 回看交易日个数
    g.min_exposure = 0.40     # 权益暴露下限
    g.max_exposure = 1.00     # 权益暴露上限
    g.default_exposure = 0.80 # 数据不足时的初始仓位
    g.max_dd_deRisk = -0.25   # 回撤超过 25% -> 降到 min_exposure

    # ---------- 分级凯莉 · 单票倾斜权重 ----------
    g.max_pos_weight = 0.10   # 单票最大权重
    g.tilt_min = 0.5          # 倾斜下限（相对等权）
    g.tilt_max = 2.0          # 倾斜上限（相对等权）

    # 状态
    g.recent_pv = collections.deque(maxlen=g.kelly_window + 5)  # 近端组合净值
    g.peak_value = 0.0                                         # 历史高点

    run_daily(track_value, time='14:55')
    run_monthly(rebalance, monthday=1, time='09:31')


# ============================================================
# 每日记录组合净值与高点（供动态凯莉/回撤使用）
# ============================================================
def track_value(context):
    v = context.portfolio.total_value
    g.recent_pv.append(v)
    if v > g.peak_value:
        g.peak_value = v


# ============================================================
# 动态分级凯莉：计算权益暴露仓
# ============================================================
def kelly_exposure(context):
    pv = list(g.recent_pv)
    if len(pv) < 60:                     # 数据不足，用默认仓位
        return g.default_exposure
    r = np.diff(pv) / np.asarray(pv[:-1], dtype=float)   # 日收益
    mu_ann = r.mean() * 250
    sd_ann = r.std() * np.sqrt(250)
    if sd_ann < 1e-6:                    # 几乎无波动
        return g.max_exposure
    kelly = (mu_ann - g.rf) / (sd_ann ** 2)
    frac = g.kelly_mult * max(0.0, kelly)
    return float(min(g.max_exposure, max(g.min_exposure, frac)))


# ============================================================
# 每月调仓入口
# ============================================================
def rebalance(context):
    date = context.current_dt.date()
    prev = context.previous_date

    try:
        # 0) 动态仓位（分级凯莉 + 回撤保护）
        exposure = kelly_exposure(context)
        cur_dd = (context.portfolio.total_value / g.peak_value - 1) if g.peak_value > 0 else 0.0
        if cur_dd < g.max_dd_deRisk:
            exposure = g.min_exposure
            log.info('烟蒂股：回撤 %.1f%% 触发保护 -> 降到 %.0f%% 仓'
                     % (cur_dd * 100, g.min_exposure * 100))
        log.info('烟蒂股：当前仓位暴露 %.0f%%' % (exposure * 100))

        # 1) 选股（与 v1 相同）
        universe = get_universe(context, prev, date)
        log.info('烟蒂股：过滤后股票池 %d 只' % len(universe))
        if not universe:
            return
        pool = get_small_cap_pool(universe, prev)
        log.info('烟蒂股：小市值池 %d 只' % len(pool))
        if not pool:
            return
        target = screen_cigar_butt(pool, prev, date)
        log.info('烟蒂股：当期烟蒂股候选 %d 只' % len(target))
        if target is None or len(target) == 0:
            return

        # 2) 分级凯莉倾斜权重（有上限）
        weights = compute_weights(target, exposure)
        log.info('烟蒂股：持有 %d 只，总仓位 %.0f%%' % (len(weights), sum(w for _, w in weights) * 100))

        # 3) 调仓（卖出/止损/再平衡）
        manage_holdings(context, weights)

        # 4) 记录
        record(context, target, exposure)

    except Exception as e:
        log.error('烟蒂股：调仓异常 %s: %s' % (type(e).__name__, e))


# ============================================================
# 1. 股票池基础过滤
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


# ============================================================
# 2. 小市值池
# ============================================================
def get_small_cap_pool(universe, prev):
    q = query(valuation.code).filter(
        valuation.code.in_(universe)
    ).order_by(valuation.market_cap.asc()).limit(g.pool_size)
    df = get_fundamentals(q, date=prev)
    if df is None or len(df) == 0:
        return []
    return df['code'].tolist()


# ============================================================
# 3. 烟蒂股筛选（股息率 + 支付率 + 市净率）
# ============================================================
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
        log.info('烟蒂股：严格候选 %d < %d，放宽支付率到 <=%.2f 后 %d'
                 % (len(strict), g.min_hold, g.payout_relax_max, len(fuzzy)))
        sel = fuzzy
    else:
        sel = strict

    top = sel.sort_values('div_yield', ascending=False).head(g.top_n)
    return top.reset_index(drop=True)


# ============================================================
# 4. 分级凯莉倾斜权重（有上限，总和=exposure）
# ============================================================
def compute_weights(target, exposure):
    df = target.copy()
    n = len(df)
    if n == 0:
        return []

    # 确定性分：股息率高、市净率低 -> 更强；用 (div_yield)/(pb+0.5) 避免除零
    score = df['div_yield'].clip(lower=1e-6) / (df['pb_ratio'] + 0.5)
    rel = score / (score.mean() if score.mean() > 0 else 1.0)
    rel = rel.clip(g.tilt_min, g.tilt_max)           # 有上限倾斜（分级凯莉）

    base = 1.0 / n
    raw = base * rel
    raw = raw.clip(upper=g.max_pos_weight)           # 单票硬上限
    total = raw.sum()
    if total <= 0:
        return []
    weights = raw * (exposure / total)                # 归一化到 exposure
    weights = weights.clip(upper=g.max_pos_weight)

    return list(zip(df['code'].tolist(), weights.tolist()))


# ============================================================
# 5. 调仓：止损/退市卖出 + 非目标调出 + 目标再平衡
# ============================================================
def manage_holdings(context, weights):
    target_map = dict(weights)
    cd = get_current_data()

    # 先处理不再持有的 + 止损/退市
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
        if stock not in target_map:
            order_target(stock, 0)
            log.info('烟蒂股：调出 %s' % stock)

    # 目标再平衡（买入/加仓/减仓统一用 order_target_value 调到目标权重）
    for stock, w in weights:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        order_target_value(stock, context.portfolio.total_value * w)


# ============================================================
# 6. 记录组合状态
# ============================================================
def record(context, target, exposure):
    try:
        value = context.portfolio.total_value
        n = len(context.portfolio.positions)
        log.info('烟蒂股：净值 %.2f | 持仓 %d | 候选 %d | 暴露 %.0f%%'
                 % (value, n, len(target), exposure * 100))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
