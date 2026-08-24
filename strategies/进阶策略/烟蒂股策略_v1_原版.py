# -*- coding: utf-8 -*-
"""
烟蒂股策略 v1 · 原版（小市值 + 高股息可持续型）—— 聚宽平台

【策略思想】
    借鉴"格雷厄姆式烟蒂股代理"：买**市值最小**、**股息率高且分红可持续**的一篮子股票。
    （"烟蒂股"按小市值 + 高股息的代理口径，而非严格 NCAV 净流动资产。）

【选股流程（每月重算）】
    全市场 A 股
      → 剔除 ST/*ST/退市、科创板(688)、北交所(4/8/920)、次新(<365天)、停牌
      → 取市值最小的 pool_size 只（小市值池）
      → 剔除股利支付率异常： payout_rate 不在 (0,1] 内（>1 分红超过利润 / ≤0 亏损或不含税）
      → 剔除市净率 ≤ 0（资不抵债的"有毒烟蒂"）
      → 按股息率（近一年分红/市值）降序取前 top_n 只 = 当期烟蒂股
      → 等权建仓（满仓）

【卖出逻辑】
    - 止损：相对成本 -20%
    - 调出：不再是当期 top_n 目标 / 不再满足股利支付率或市净率条件
    - 退市 / ST

【A/B】v1 原版(等权满仓) / v2 正向凯莉 / v3 逆向凯莉 —— 三者选股完全相同，只差仓位管理。

【注意】财务/分红/估值一律用前一日数据（prev_date），避免未来函数。本策略为学习/研究用途，不构成投资建议。
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

    # ---------- 可调参数 ----------
    g.pool_size = 1000        # 市值最小的 N 只（候选池）
    g.top_n = 10              # 最终持有/买入数量（股息率降序）
    g.min_hold = 5            # 严格筛选候选低于此数时，放宽支付率上限兜底建仓
    g.payout_relax_max = 2.0  # 兜底时的支付率上限（分红 ≤ 2×净利润，避免病态高分红）
    g.max_div_yield = 0.40    # 股息率上限（>40% 多为特别分红/股价崩塌，剔除）
    g.min_circ_mcap = 1.0     # 最小流通市值（亿元），仅剔除极端小盘
    g.payout_min = 0.0        # 股利支付率下限（>0：有盈利才分红）
    g.payout_max = 1.0        # 股利支付率上限（<=1：分红不超过利润，可持续）
    g.min_list_days = 365     # 上市不足此天数剔除（次新股）
    g.stop_loss = -0.20       # 相对成本止损线（-20%）

    run_monthly(rebalance, monthday=1, time='09:31')


def rebalance(context):
    date = context.current_dt.date()      # 仅用于股票池/上市时长判断
    prev = context.previous_date          # 所有财务/分红/估值数据统一用前一日

    try:
        universe = get_universe(context, prev, date)
        log.info('烟蒂股v1：过滤后股票池 %d 只' % len(universe))
        if not universe:
            return

        pool = get_small_cap_pool(universe, prev)
        log.info('烟蒂股v1：小市值池 %d 只' % len(pool))
        if not pool:
            return

        target = screen_cigar_butt(pool, prev, date)
        log.info('烟蒂股v1：当期烟蒂股候选 %d 只' % len(target))

        sell_holdings(context, target, prev)
        buy_holdings(context, target)
        record(context, target)

    except Exception as e:
        log.error('烟蒂股v1：调仓异常 %s: %s' % (type(e).__name__, e))


def get_universe(context, prev, date):
    all_sec = get_all_securities(types=['stock'], date=date)
    if all_sec is None or len(all_sec) == 0:
        return []

    cd = get_current_data()
    kept = []
    for code in all_sec.index:
        # 剔除科创/北交
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
    ).order_by(
        valuation.market_cap.asc()
    ).limit(g.pool_size)
    df = get_fundamentals(q, date=prev)
    if df is None or len(df) == 0:
        return []
    return df['code'].tolist()


def screen_cigar_butt(pool, prev, date):
    if not pool:
        return pd.DataFrame()

    # ---- 近一年现金分红（元）----
    time0 = prev - datetime.timedelta(days=365)
    f = finance.STK_XR_XD
    q = query(
        f.code, f.bonus_ratio_rmb, f.total_capital_before_transfer, f.a_registration_date
    ).filter(
        f.code.in_(pool),
        f.a_registration_date >= time0,
        f.a_registration_date <= prev,
    )
    dd = finance.run_query(q)
    if dd is None or len(dd) == 0:
        return pd.DataFrame()
    dd = dd.fillna(0)
    # 每股派息(元) × 总股本(股) = 本次分红总额(元)；bonus_ratio_rmb 按每 10 股派息口径
    dd['cash_div'] = (dd['bonus_ratio_rmb'] / 10) * dd['total_capital_before_transfer'] * 1e4
    div = dd.groupby('code')['cash_div'].sum()

    # ---- 估值 / 盈利 ----
    q2 = query(
        valuation.code, valuation.market_cap, valuation.circulating_market_cap,
        valuation.pe_ratio, valuation.pb_ratio,
    ).filter(valuation.code.in_(div.index))
    fund = get_fundamentals(q2, date=prev)
    if fund is None or len(fund) == 0:
        return pd.DataFrame()
    cap = fund.set_index('code')

    # ---- 合并计算 ----
    df = pd.concat([div, cap], axis=1, sort=False).reset_index()
    df['cash_div'] = df['cash_div'] / 1e8                # 元 → 亿
    df['div_yield'] = df['cash_div'] / df['market_cap']  # 股息率
    df['net_profit'] = df['market_cap'] / df['pe_ratio'] # 净利润 TTM（亿）
    df['payout_rate'] = df['cash_div'] / df['net_profit']# 股利支付率

    # ---- 过滤：先严格（支付率 <= 1），不足则放宽到 payout_relax_max，但始终要求 正盈利+正市净率+有分红 ----
    df = df.dropna(subset=['div_yield', 'payout_rate', 'pb_ratio', 'market_cap'])
    has_profit_pb = (df['payout_rate'] > g.payout_min) & (df['pb_ratio'] > 0)
    if 'circulating_market_cap' in df.columns:
        has_profit_pb = has_profit_pb & (df['circulating_market_cap'] >= g.min_circ_mcap)
    # 剔除股息率异常高（多为特别分红/股价崩塌）的标的
    has_sane_yield = df['div_yield'] <= g.max_div_yield

    strict = df[has_profit_pb & has_sane_yield & (df['payout_rate'] <= g.payout_max)]
    if len(strict) < g.min_hold:
        fuzzy = df[has_profit_pb & has_sane_yield & (df['payout_rate'] <= g.payout_relax_max)]
        log.info('烟蒂股v1：严格候选 %d < %d，放宽支付率到 <=%.2f 后 %d'
                 % (len(strict), g.min_hold, g.payout_relax_max, len(fuzzy)))
        sel = fuzzy
    else:
        sel = strict

    # ---- 股息率降序取 top_n ----
    top = sel.sort_values('div_yield', ascending=False).head(g.top_n)
    return top.reset_index(drop=True)


def sell_holdings(context, target, prev):
    target_codes = set(target['code'].tolist()) if target is not None and len(target) else set()
    cd = get_current_data()
    for stock, pos in list(context.portfolio.positions.items()):
        if pos.closeable_amount <= 0:
            continue
        cur = cd[stock]
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            order_target(stock, 0)
            log.info('烟蒂股v1：退市/ST 卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股v1：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        # 不再是当期烟蒂目标 → 调出
        if stock not in target_codes:
            order_target(stock, 0)
            log.info('烟蒂股v1：调出 %s' % stock)


def buy_holdings(context, target):
    if target is None or len(target) == 0:
        return
    codes = target['code'].tolist()
    cd = get_current_data()
    weight = 1.0 / len(codes)   # 等权、满仓
    for stock in codes:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        order_target_value(stock, context.portfolio.total_value * weight)


def record(context, target):
    try:
        value = context.portfolio.total_value
        cash = context.portfolio.available_cash
        n = len(context.portfolio.positions)
        log.info('烟蒂股v1：净值 %.2f | 现金 %.2f | 持仓 %d | 候选 %d'
                 % (value, cash, n, len(target) if target is not None else 0))
        record(value=value)
        if target is not None and len(target) > 0:
            record(avg_div_yield=target['div_yield'].mean())
    except Exception:
        pass
