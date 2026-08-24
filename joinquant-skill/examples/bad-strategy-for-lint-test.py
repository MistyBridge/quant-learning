# 这是一个故意写错的策略，用来演示 lint 工具的检测能力
# python scripts/strategy_lint.py examples/bad-strategy-for-lint-test.py

import jqdata


def initialize(context):
    # ❌ JQ001: 调用不存在的 set_initial_cash
    set_initial_cash(100000)

    # ✅ 正确的基准
    set_benchmark('000300.XSHG')

    # ❌ JQ010 warning: 没有 set_option('use_real_price', True)
    # ❌ JQ011 warning: 没有 set_order_cost
    # ❌ JQ012 warning: 没有 set_slippage

    g.security = '000001.XSHE'

    run_daily(market_open, time='open')


def before_trading_start(context):
    # ❌ JQ004: 在 before_trading_start 里下单（聚宽禁止）
    order(g.security, 1000)


def market_open(context):
    # ❌ JQ001: get_stock_data 不存在
    df = get_stock_data(g.security, days=20)

    # ❌ JQ001: get_history_data 不存在
    prices = get_history_data(g.security, 5)

    # ❌ JQ001: get_realtime_quote 不存在
    quote = get_realtime_quote(g.security)

    # ❌ JQ001: get_account_balance 不存在
    cash = get_account_balance()

    # ❌ JQ002: update_universe 已废弃
    update_universe(['000001.XSHE'])

    # ❌ JQ001: place_order / submit_order 不存在
    place_order(g.security, 100)


def after_trading_end(context):
    # ❌ JQ004: 在 after_trading_end 里下单
    order_value(g.security, 5000)
