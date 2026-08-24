#!/usr/bin/env python3
"""
strategy_scaffold.py — 根据策略类型生成聚宽策略骨架

用法:
    python scripts/strategy_scaffold.py --type rotation --output my_strategy.py
    python scripts/strategy_scaffold.py --type momentum --security 000300.XSHG --output mom.py
    python scripts/strategy_scaffold.py --list

支持的 type:
    basic         单股票均线（最简单）
    multi-factor  多因子选股 + 月度调仓
    rotation      ETF 动量轮动
    momentum      股票横截面动量
    mean-reversion 布林带 + RSI 均值回归
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR.parent / 'templates'

TEMPLATE_MAP = {
    'basic': '01-basic-single-stock.py',
    'multi-factor': '02-multi-factor.py',
    'multi_factor': '02-multi-factor.py',
    'rotation': '03-etf-rotation.py',
    'etf': '03-etf-rotation.py',
    'momentum': '04-momentum-stock.py',
    'mean-reversion': '05-mean-reversion.py',
    'mean_reversion': '05-mean-reversion.py',
    'reversion': '05-mean-reversion.py',
}

DESCRIPTIONS = {
    '01-basic-single-stock.py': '单股票 5/20 日均线策略（入门）',
    '02-multi-factor.py': '多因子选股（PE/市值/动量），月度调仓',
    '03-etf-rotation.py': '10 ETF 动量轮动，月度调仓',
    '04-momentum-stock.py': '股票横截面动量，周度调仓',
    '05-mean-reversion.py': '布林带 + RSI 均值回归',
}


def list_templates() -> None:
    print('Available templates:')
    print('-' * 60)
    for name in sorted(set(TEMPLATE_MAP.values())):
        path = TEMPLATE_DIR / name
        size_kb = path.stat().st_size / 1024 if path.exists() else 0
        desc = DESCRIPTIONS.get(name, '')
        print(f'  {name:<30} {size_kb:.1f} KB  {desc}')
    print()
    print('Type aliases:')
    for alias, target in sorted(TEMPLATE_MAP.items()):
        if alias != target:
            print(f'  --type {alias:<18} → {target}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Generate JoinQuant strategy scaffold from template',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Run with --list to see all templates.',
    )
    parser.add_argument('--type', help='Strategy type (basic / multi-factor / rotation / momentum / mean-reversion)')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--security', help='Override default security (e.g. 510300.XSHG)')
    parser.add_argument('--universe', help='Override universe index (e.g. 000300.XSHG)')
    parser.add_argument('--hold-num', type=int, help='Override hold count (multi-factor / momentum)')
    parser.add_argument('--list', action='store_true', help='List available templates')

    args = parser.parse_args()

    if args.list:
        list_templates()
        return 0

    if not args.type:
        parser.error('--type is required (or use --list to see options)')
        return 2

    template_name = TEMPLATE_MAP.get(args.type)
    if not template_name:
        print(f'[error] Unknown type: {args.type}', file=sys.stderr)
        print(f'[hint] Available: {", ".join(sorted(set(TEMPLATE_MAP.values())))}', file=sys.stderr)
        return 1

    src = TEMPLATE_DIR / template_name
    if not src.exists():
        print(f'[error] Template file missing: {src}', file=sys.stderr)
        return 1

    content = src.read_text(encoding='utf-8')

    # 简单的覆盖：替换默认参数
    if args.security:
        # 替换 g.security = '...'
        import re
        content = re.sub(r"g\.security = '[^']+'",
                         f"g.security = '{args.security}'", content, count=1)

    if args.universe:
        import re
        content = re.sub(r"g\.universe_index = '[^']+'",
                         f"g.universe_index = '{args.universe}'", content, count=1)

    if args.hold_num:
        import re
        content = re.sub(r"g\.hold_num = \d+",
                         f"g.hold_num = {args.hold_num}", content, count=1)
        content = re.sub(r"g\.top_k = \d+",
                         f"g.top_k = {args.hold_num}", content, count=1)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding='utf-8')
        print(f'[ok] Strategy generated: {out}')
        print()
        print('Next steps:')
        print(f'  1. Edit {out.name} to customize parameters')
        print(f'  2. Run lint: python scripts/strategy_lint.py {out}')
        print(f'  3. Copy-paste to JoinQuant online editor')
    else:
        print(content)

    return 0


if __name__ == '__main__':
    sys.exit(main())
