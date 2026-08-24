# -*- coding: utf-8 -*-
"""
烟蒂股策略 v7 · 因子避险版（小微盘指数 120日线生命线 + 标准差定比例）—— 聚宽平台

【设计】
    在 v1(小市值+高股息, top_n=10, 等权满仓)基础上, 加一个**小微盘指数风险因子开关**:
      - 生命线: 参考指数的 120 日均线;
      - 每日检查: z = (指数现价 - 120日均线) / 120日标准差  (标准差作为"比例"的度量单位);
      - 暴露 E = min_exposure + (max_exposure - min_exposure) * tanh(z / transition),
        z>0(高于生命线, 积极状态)-> 接近满仓; z<0(低于生命线, 消极状态)-> 接近最低仓;
        夹在 [min_exposure, max_exposure]。
      - 只有当 E 目标变化超过 exposure_band 才调仓(避免每日换手); 换股仍为月度 top_n=10 等权。

【注意】
    - 参考指数代码 g.risk_index 需在聚宽里换成真正的小微盘指数(如 中证2000/国证2000)。
      默认写的是中证1000(000852.XSHG, 偏中盘), 仅保证能跑通, 请务必替换!
    - "用标准差定比例"属于朴素可解释信号; 阈值/带宽请在样本外做敏感性检验, 避免过拟合。
    - 本策略为学习/研究用途, 不构成投资建议。
"""

from jqdata import *
import pandas as pd
import numpy as np
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

    # ---- 风险因子开关(小微盘指数 120日线)----
    g.risk_index = '000852.XSHG'   # ⚠️ 请务必替换成真正的小微盘指数(如 中证2000/国证2000)
    g.ma_window = 120              # 生命线: 120 日均线
    g.transition = 1.0             # 生命线过渡宽度(越小越接近"硬开关")
    g.min_exposure = 0.50          # 消极状态最低暴露(50% 仓)
    g.max_exposure = 1.00          # 积极状态最高暴露(满仓)
    g.exposure_band = 0.10         # 暴露目标变化超过该幅度才调仓(控换手)

    g.target_codes = []            # 当期目标(月度更新)
    g.exposure = 0.75              # 当前暴露目标

    # 每日检查风险因子; 每月换股并应用暴露
    run_daily(risk_check, time='09:45')
    run_monthly(rebalance, monthday=1, time='09:31')


# ============================================================
# 每日风险因子开关: 计算目标暴露并(带宽内)调仓
# ============================================================
def risk_check(context):
    try:
        E = compute_target_exposure(context)
        if E is None:
            return
        if abs(E - g.exposure) >= g.exposure_band:
            g.exposure = E
            log.info('烟蒂股v7：风险因子 z 变化 -> 暴露 %.0f%%' % (E * 100))
            apply_weights(context)
    except Exception as e:
        log.error('烟蒂股v7：风险检查异常 %s: %s' % (type(e).__name__, e))


# ============================================================
# 用小微盘指数 120 日线 + 标准差算目标暴露
# ============================================================
def compute_target_exposure(context):
    try:
        df = get_price(g.risk_index, count=g.ma_window + 1,
                       end_date=context.previous_date, fields=['close'], panel=False)
        if df is None or len(df) < g.ma_window:
            return None
        close = df['close'].values
        ma = close.mean()
        std = close.std()
        if std < 1e-9:
            return None
        z = (close[-1] - ma) / std                    # 偏离生命线的标准差个数
        frac = 0.5 * (1 + np.tanh(z / g.transition))  # 0~1, 越高生命线越积极
        E = g.min_exposure + (g.max_exposure - g.min_exposure) * frac
        return float(min(g.max_exposure, max(g.min_exposure, E)))
    except Exception:
        return None


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
        E = compute_target_exposure(context)
        if E is not None:
            g.exposure = E
        apply_weights(context)
        record(context, target)
    except Exception as e:
        log.error('烟蒂股v7：调仓异常 %s: %s' % (type(e).__name__, e))


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
            log.info('烟蒂股v7：退市/ST 卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股v7：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        if stock not in target_codes:
            order_target(stock, 0)
            log.info('烟蒂股v7：调出 %s' % stock)

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
        log.info('烟蒂股v7：净值 %.2f | 持仓 %d | 候选 %d | 暴露 %.0f%%'
                 % (value, n, len(target), g.exposure * 100))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
