# -*- coding: utf-8 -*-
"""
烟蒂股策略（Graham Net-Net / Deep-Value）—— 聚宽平台

【策略思想】
    格雷厄姆"烟蒂股"：买入市值低于"净流动资产价值"（Net Current Asset Value, NCAV）的股票，
    相当于"用五毛钱买一块钱"。口径：
        NCAV = 流动资产合计 - 总负债（含长期负债，取保守口径）
        基础买入条件：总市值 < NCAV            （标准净流动资产 / 烟蒂股，P/NCAV < 1）
    由于 A 股严格"市值 < NCAV"的标的随行情稀少，本策略做了**自适应放宽**：
        先取 `市值/NCAV` 最小的、满足 `总市值 ≤ NCAV * buy_threshold` 的标的；
        若当月候选不足 `min_candidates` 个，自动把阈值放宽到 `max_buy_ratio`，
        以便在市场没有严格烟蒂股时，仍能买入"最接近净流动资产"的深度价值股。

【卖出逻辑】
    - 止损：相对成本 -20%
    - 价值兑现：总市值 ≥ NCAV * sell_threshold（明显高于买入上限，先涨后卖）
    - 退市 / ST / NCAV 转负

【运行方式】
    复制到聚宽在线编辑器直接回测。可调参数见 initialize 的 g.*。
    日志会输出每个月的"筛选漏斗"，用于核对为何买/不买。

【注意】本策略为量化学习/研究用途，不构成投资建议。
"""

from jqdata import *
import pandas as pd


# ============================================================
# 初始化：整个回测开始时运行一次
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

    # ---------- 可调参数 ----------
    g.buy_threshold = 1.0      # 基础买入：总市值 <= NCAV（标准净流动资产/烟蒂股）
    g.max_buy_ratio = 1.25     # 候选不足时，最多放宽到 总市值 <= 1.25 * NCAV（深度价值）
    g.min_candidates = 5       # 候选少于该数则触发放宽
    g.top_n = 10               # 最大持仓数量（等权）
    g.sell_threshold = 1.5     # 价值兑现：总市值 >= 1.5 * NCAV 卖出
    g.stop_loss = -0.20        # 相对成本止损线（-20%）
    g.min_list_days = 365      # 上市不足此天数剔除（次新股）
    g.min_circ_mcap = 2.0      # 最小流通市值（亿元），过滤小盘/流动性差标的

    run_monthly(rebalance, monthday=1, time='09:31')


# ============================================================
# 每月调仓入口
# ============================================================
def rebalance(context):
    prev_date = context.previous_date
    date = context.current_dt.date()

    try:
        universe = get_universe(context, prev_date, date)
        log.info('烟蒂股：本轮股票池 %d 只' % len(universe))
        if not universe:
            log.info('烟蒂股：无候选股票池')
            return

        fund = query_fundamentals(universe, prev_date)
        if fund is None or len(fund) == 0:
            log.info('烟蒂股：无财务数据')
            return
        log.info('烟蒂股：取到财务数据 %d 行' % len(fund))

        cand = compute_candidates(fund, prev_date)

        sell_holdings(context, cand, prev_date)
        buy_holdings(context, cand)
        record_holdings(context, cand)

    except Exception as e:
        log.error('烟蒂股：调仓异常 %s: %s' % (type(e).__name__, e))


# ============================================================
# 1. 股票池与基础过滤
# ============================================================
def get_universe(context, prev_date, date):
    all_sec = get_all_securities(types=['stock'], date=prev_date)
    if all_sec is None or len(all_sec) == 0:
        return []

    cd = get_current_data()
    kept = []
    for code in all_sec.index:
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
# 2. 批量取财务数据（分批避免超 5000 行限制）
# ============================================================
def query_fundamentals(universe, prev_date):
    frames = []
    size = 400
    for i in range(0, len(universe), size):
        chunk = universe[i:i + size]
        q = query(
            valuation.code,
            balance.total_current_assets,      # 流动资产合计
            balance.total_liability,            # 负债合计（含长期，保守口径）
            valuation.market_cap,               # 总市值（亿元）
            valuation.circulating_market_cap,   # 流通市值（亿元）
        ).filter(valuation.code.in_(chunk))
        df = get_fundamentals(q, date=prev_date)
        if df is not None and len(df) > 0:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ============================================================
# 3. 计算 NCAV / P/NCAV 并自适应选股
# ============================================================
def compute_candidates(fund, prev_date):
    if fund is None or len(fund) == 0:
        return pd.DataFrame()

    df = fund.copy()
    df = df.dropna(subset=['total_current_assets', 'total_liability', 'market_cap'])
    df = df[(df['total_current_assets'] > 0) & (df['total_liability'] > 0)]

    # NCAV = 流动资产合计 - 总负债（保守口径）
    df['ncav'] = df['total_current_assets'] - df['total_liability']
    df = df[df['ncav'] > 0]

    # 市值（亿元）换算为元，计算 P/NCAV
    df['mcap_yuan'] = df['market_cap'] * 1e8
    df['ratio'] = df['mcap_yuan'] / df['ncav']
    df['code'] = df['code'].astype(str)

    log.info('烟蒂股：NCAV>0 的股票 %d 只' % len(df))

    # 剔除金融类（银行/证券/保险/信托等，其资产负债表结构不适用烟蒂股）
    keep = exclude_financial(df['code'].tolist(), prev_date)
    df = df[df['code'].isin(keep)]

    # 流动性门槛：流通市值（亿元）
    if 'circulating_market_cap' in df.columns:
        df = df[df['circulating_market_cap'] >= g.min_circ_mcap]

    # 按折扣深度（P/NCAV 越小越好）排序
    df = df.sort_values('ratio').reset_index(drop=True)

    # 自适应阈值：先严格净流动资产，不够则放宽
    sel = df[df['ratio'] <= g.buy_threshold]
    cap = g.buy_threshold
    while len(sel) < g.min_candidates and cap < g.max_buy_ratio:
        cap = round(cap + 0.05, 2)
        sel = df[df['ratio'] <= cap]

    log.info('烟蒂股：买入阈值 P/NCAV<=%.2f，候选 %d 只' % (cap, len(sel)))
    return sel.reset_index(drop=True)


# ============================================================
# 剔除金融行业
# ============================================================
def exclude_financial(codes, date):
    if not codes:
        return []
    try:
        ind = get_industry(codes, date=date)
    except Exception:
        return codes  # 容错：取不到行业时不剔除，避免误杀

    kw = ('银行', '证券', '保险', '信托', '期货', '金融', '多元金融', '货币金融')
    keep = []
    for c in codes:
        d = ind.get(c)
        if not d:
            keep.append(c)
            continue
        try:
            name = str(d['jq_l1']['industry_name']) + str(d['sw_l1']['industry_name'])
        except Exception:
            name = ''
        if any(k in name for k in kw):
            continue
        keep.append(c)
    return keep


# ============================================================
# 4. 卖出逻辑：止损 / 价值兑现 / 退市风险
# ============================================================
def sell_holdings(context, cand, prev_date):
    cd = get_current_data()
    for stock, pos in list(context.portfolio.positions.items()):
        if pos.closeable_amount <= 0:
            continue
        cur = cd[stock]
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            order_target(stock, 0)
            log.info('烟蒂股：退市/ST 风险卖出 %s' % stock)
            continue
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        ratio = current_ratio(stock, prev_date)
        if ratio is not None and ratio >= g.sell_threshold:
            order_target(stock, 0)
            log.info('烟蒂股：价值兑现卖出 %s (P/NCAV=%.3f)' % (stock, ratio))
            continue
        if ratio is not None and ratio < 0:
            order_target(stock, 0)
            log.info('烟蒂股：NCAV 转负卖出 %s' % stock)


# ============================================================
# 5. 买入 / 再平衡（等权）
# ============================================================
def buy_holdings(context, cand):
    if cand is None or len(cand) == 0:
        return
    target = cand.head(g.top_n)['code'].tolist()
    keep = set(target)

    for stock, pos in list(context.portfolio.positions.items()):
        if stock not in keep and pos.closeable_amount > 0:
            order_target(stock, 0)
            log.info('烟蒂股：调出 %s' % stock)

    if not target:
        return

    cd = get_current_data()
    weight = 1.0 / len(target)
    for stock in target:
        cur = cd[stock]
        if cur.paused or cur.is_st:
            continue
        order_target_value(stock, context.portfolio.total_value * weight)


# ============================================================
# 单只股票当前的 P/NCAV（用于卖出判断）
# ============================================================
def current_ratio(code, date):
    q = query(
        valuation.code,
        balance.total_current_assets,
        balance.total_liability,
        valuation.market_cap,
    ).filter(valuation.code == code)
    df = get_fundamentals(q, date=date)
    if df is None or len(df) == 0:
        return None
    row = df.iloc[0]
    tca = row['total_current_assets']
    tl = row['total_liability']
    mcap = row['market_cap']
    if pd.isnull(tca) or pd.isnull(tl) or pd.isnull(mcap):
        return None
    ncav = tca - tl
    if ncav <= 0:
        return -1.0
    return (mcap * 1e8) / ncav


# ============================================================
# 记录组合状态
# ============================================================
def record_holdings(context, cand):
    try:
        value = context.portfolio.total_value
        cash = context.portfolio.available_cash
        n = len(context.portfolio.positions)
        log.info('烟蒂股：组合净值 %.2f | 现金 %.2f | 持仓 %d | 候选 %d'
                 % (value, cash, n, len(cand) if cand is not None else 0))
        record(value=value)
        if cand is not None and len(cand) > 0:
            record(avg_ratio=cand.head(g.top_n)['ratio'].mean())
    except Exception:
        pass
