# -*- coding: utf-8 -*-
"""
烟蒂股策略（Graham Net-Net / Cigar-Butt Strategy）—— 聚宽平台

【策略思想】
    格雷厄姆"烟蒂股"：买入市价低于"净流动资产价值"（Net Current Asset Value, NCAV）的股票，
    相当于"用五毛钱买一块钱"。经典口径：
        NCAV = 流动资产合计 - 总负债（含长期负债，取保守口径）
        买入条件：总市值 < NCAV * buy_threshold   （即 P/NCAV < threshold）
        经典格雷厄姆阈值：threshold = 2/3 ≈ 0.667
    卖出逻辑：当市值回到接近/超过 NCAV（价值兑现），或触发止损时卖出。

【适用场景】
    熊市 / 小盘 / 深度价值行情中机会较多。适合作为价值风格的一篮子选股策略。

【使用方法】
    复制本文件全部代码到聚宽在线编辑器（我的策略 -> 新建策略），直接运行回测。
    可调参数见 initialize 中的 g.* 全局变量。

【注意】
    - 本策略为量化学习/研究用途，不构成投资建议。
    - 财务口径以聚宽 balance 表为准；不同报告期数据更新有滞后，回测默认用前一日数据避免未来函数。
"""

from jqdata import *
import pandas as pd


# ============================================================
# 初始化：整个回测开始时运行一次
# ============================================================
def initialize(context):
    # 基准：沪深300
    set_benchmark('000300.XSHG')
    # 使用真实价格（非前复权），避免未来函数
    set_option('use_real_price', True)

    # 交易成本与滑点（必填，否则回测失真）
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(PriceRelatedSlippage(0.00246))

    # ---------- 可调参数 ----------
    g.buy_threshold = 0.667      # 买入阈值：市值 < NCAV * 2/3（格雷厄姆净流动资产标准）
    g.sell_threshold = 0.90      # 卖出阈值：市值 >= NCAV * 0.9（净值大幅兑现）
    g.top_n = 10                 # 最大持仓数量（等权）
    g.stop_loss = -0.20          # 相对成本止损线（-20%）
    g.min_list_days = 365        # 上市不足此天数剔除（次新股）
    g.min_circ_mcap = 3.0        # 最小流通市值（亿元），过滤小盘/流动性差标的

    # 每月第一个交易日调仓
    run_monthly(rebalance, monthday=1, time='09:31')


# ============================================================
# 每月调仓入口
# ============================================================
def rebalance(context):
    # 财务/估值用前一日数据，避免用到当天未发布的未来数据
    prev_date = context.previous_date
    date = context.current_dt.date()

    try:
        # 1) 全市场股票池 + 基础过滤（上市时长 / ST / 停牌）
        universe = get_universe(context, prev_date, date)
        if not universe:
            log.info('烟蒂股：无候选股票池')
            return

        # 2) 批量取财务（资产负债表 + 估值），分批避免超 5000 行限制
        fund = query_fundamentals(universe, prev_date)
        if fund is None or len(fund) == 0:
            log.info('烟蒂股：无财务数据')
            return

        # 3) 计算 NCAV 与 P/NCAV，输出候选（已做质量/行业/流动性过滤）
        cand = compute_candidates(fund, context, date, prev_date)

        # 4) 先处理卖出（止损 / 价值兑现 / 退市风险）
        sell_holdings(context, cand, prev_date)

        # 5) 再平衡买入
        buy_holdings(context, cand)

        # 记录持仓与组合估值
        record_holdings(context, cand)

    except Exception as e:
        # 单次调仓异常不中断整个回测，打印后跳过本月
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
        # 上市不足 N 天：剔除次新股
        try:
            if (date - info['start_date']).days < g.min_list_days:
                continue
        except Exception:
            pass
        cur = cd[code]
        # 停牌、ST、退市整理期、名称含退市：剔除
        if cur.paused:
            continue
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            continue
        kept.append(code)
    return kept


# ============================================================
# 2. 批量取财务数据
# ============================================================
def query_fundamentals(universe, prev_date):
    frames = []
    size = 400
    for i in range(0, len(universe), size):
        chunk = universe[i:i + size]
        q = query(
            valuation.code,
            balance.total_current_assets,     # 流动资产合计
            balance.total_liabilities,         # 负债合计（含长期，保守口径）
            valuation.market_cap,              # 总市值（亿元）
            valuation.circulating_market_cap,  # 流通市值（亿元）
        ).filter(valuation.code.in_(chunk))
        df = get_fundamentals(q, date=prev_date)
        if df is not None and len(df) > 0:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ============================================================
# 3. 计算 NCAV / P/NCAV，筛选候选
# ============================================================
def compute_candidates(fund, context, date, prev_date):
    if fund is None or len(fund) == 0:
        return pd.DataFrame()

    df = fund.copy()
    # 缺失关键数据剔除
    df = df.dropna(subset=['total_current_assets', 'total_liabilities', 'market_cap'])
    df = df[df['total_current_assets'] > 0]
    df = df[df['total_liabilities'] > 0]

    # NCAV = 流动资产合计 - 总负债（保守口径）
    df['ncav'] = df['total_current_assets'] - df['total_liabilities']
    df = df[df['ncav'] > 0]

    # 市值（亿元）换算为元，计算 P/NCAV
    df['mcap_yuan'] = df['market_cap'] * 1e8
    df['ratio'] = df['mcap_yuan'] / df['ncav']

    # 买入阈值过滤
    df = df[df['ratio'] < g.buy_threshold]
    if len(df) == 0:
        return pd.DataFrame()

    df['code'] = df['code'].astype(str)

    # 剔除金融类（银行/证券/保险/信托等），它们的资产负债表结构不适用烟蒂股
    keep = exclude_financial(df['code'].tolist(), prev_date)
    df = df[df['code'].isin(keep)]

    # 流动性门槛：流通市值（亿元）
    if 'circulating_market_cap' in df.columns:
        df = df[df['circulating_market_cap'] >= g.min_circ_mcap]

    # 深度折价在前
    df = df.sort_values('ratio')
    return df.reset_index(drop=True)


# ============================================================
# 剔除金融行业
# ============================================================
def exclude_financial(codes, date):
    if not codes:
        return []
    try:
        ind = get_industry(codes, date=date)
    except Exception:
        # 取不到行业时容错：不剔除，避免误杀
        return codes

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
    cand_codes = set(cand['code'].tolist()) if len(cand) else set()
    cd = get_current_data()
    for stock, pos in list(context.portfolio.positions.items()):
        if pos.closeable_amount <= 0:
            continue
        # 退市 / ST 风险：清仓
        cur = cd[stock]
        name = cur.name or ''
        if cur.is_st or 'ST' in name.upper() or '*' in name or '退' in name:
            order_target(stock, 0)
            log.info('烟蒂股：退市/ST风险卖出 %s' % stock)
            continue
        # 止损
        avg_cost = pos.avg_cost
        last = cur.last_price
        if avg_cost > 0 and last > 0 and (last / avg_cost - 1) <= g.stop_loss:
            order_target(stock, 0)
            log.info('烟蒂股：止损卖出 %s (%.1f%%)' % (stock, (last / avg_cost - 1) * 100))
            continue
        # 价值兑现：市值回到 NCAV 的 sell_threshold 以上
        ratio = current_ratio(stock, prev_date)
        if ratio is not None and ratio >= g.sell_threshold:
            order_target(stock, 0)
            log.info('烟蒂股：价值兑现卖出 %s (P/NCAV=%.3f)' % (stock, ratio))
            continue
        # 基本面恶化（不再满足净流动资产为正）：卖出
        if ratio is not None and ratio < 0:
            order_target(stock, 0)
            log.info('烟蒂股：NCAV转负卖出 %s' % stock)


# ============================================================
# 5. 买入 / 再平衡（等权）
# ============================================================
def buy_holdings(context, cand):
    if cand is None or len(cand) == 0:
        return
    target = cand.head(g.top_n)['code'].tolist()
    keep = set(target)

    # 先调出不再持有的票
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
        balance.total_liabilities,
        valuation.market_cap,
    ).filter(valuation.code == code)
    df = get_fundamentals(q, date=date)
    if df is None or len(df) == 0:
        return None
    row = df.iloc[0]
    tca = row['total_current_assets']
    tl = row['total_liabilities']
    mcap = row['market_cap']
    if pd.isnull(tca) or pd.isnull(tl) or pd.isnull(mcap):
        return None
    ncav = tca - tl
    if ncav <= 0:
        return -1.0
    return (mcap * 1e8) / ncav


# ============================================================
# 记录每日组合状态（可选）
# ============================================================
def record_holdings(context, cand):
    try:
        value = context.portfolio.total_value
        cash = context.portfolio.available_cash
        n = len(context.portfolio.positions)
        log.info('烟蒂股：组合净值 %.2f | 现金 %.2f | 持仓 %d | 候选 %d' % (value, cash, n, len(cand) if cand is not None else 0))

        record(value=value)
        if cand is not None and len(cand) > 0:
            # 记录组合平均 P/NCAV（越小越便宜）
            record(avg_ratio=cand.head(g.top_n)['ratio'].mean())
    except Exception:
        pass
