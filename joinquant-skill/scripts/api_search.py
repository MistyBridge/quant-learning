#!/usr/bin/env python3
"""
api_search.py — 在 api.txt 里搜索 API 函数 / 关键词

用法:
    python scripts/api_search.py get_price             # 搜函数名
    python scripts/api_search.py 平行趋势              # 搜中文关键词
    python scripts/api_search.py --regex "set_\\w+"   # 正则
    python scripts/api_search.py --context 10 fq       # 显示更多上下文
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

API_FILE = Path(__file__).resolve().parent.parent / 'api文档' / 'api.txt'


def main() -> int:
    parser = argparse.ArgumentParser(description='Search JoinQuant API doc')
    parser.add_argument('keyword', help='Keyword (or regex with --regex)')
    parser.add_argument('--regex', action='store_true', help='Treat keyword as regex')
    parser.add_argument('--context', '-C', type=int, default=3,
                        help='Lines of context around match (default 3)')
    parser.add_argument('--max-matches', '-n', type=int, default=20,
                        help='Max matches to show (default 20)')
    parser.add_argument('--ignore-case', '-i', action='store_true', default=True)
    args = parser.parse_args()

    if not API_FILE.exists():
        print(f'[error] API file not found: {API_FILE}', file=sys.stderr)
        return 1

    flags = re.IGNORECASE if args.ignore_case else 0
    pattern = args.keyword if args.regex else re.escape(args.keyword)
    regex = re.compile(pattern, flags)

    lines = API_FILE.read_text(encoding='utf-8', errors='replace').splitlines()

    matches = []
    for i, line in enumerate(lines):
        if regex.search(line):
            matches.append(i)

    if not matches:
        print(f'No match for: {args.keyword}', file=sys.stderr)
        return 1

    print(f'Found {len(matches)} matches for "{args.keyword}". Showing first {min(len(matches), args.max_matches)}.')
    print('=' * 70)

    for n, idx in enumerate(matches[:args.max_matches], start=1):
        print(f'\n[Match {n}] line {idx + 1}')
        print('-' * 70)
        start = max(0, idx - args.context)
        end = min(len(lines), idx + args.context + 1)
        for j in range(start, end):
            marker = '>' if j == idx else ' '
            print(f'{marker} {j + 1:5d} | {lines[j]}')

    if len(matches) > args.max_matches:
        print(f'\n... and {len(matches) - args.max_matches} more matches.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
