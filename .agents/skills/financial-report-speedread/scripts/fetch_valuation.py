#!/usr/bin/env python3
"""
实时估值与历史分位数获取工具 (A股 / 港股)
直接调用成熟财经接口（东财/腾讯实时行情 + 百度股市通官方历史估值序列）。
用于财报速览硬门禁 G3（市值/PE/分位数实测）的标准化取数。
支持：现价、总市值、PE(TTM)、PB、实时外汇折算、PE历史分位数、中位数与极值。
"""

import sys
import json
import argparse
import urllib.parse
import requests
from datetime import datetime

def get_hkd_cny_rate():
    """获取实时港元兑人民币汇率中间价"""
    try:
        r = requests.get(
            'https://hq.sinajs.cn/list=fx_shkdcny',
            headers={'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'},
            timeout=3
        )
        if r.status_code == 200 and '="' in r.text:
            content = r.text.split('="')[1]
            parts = content.split(',')
            if len(parts) > 1 and float(parts[1]) > 0:
                return round(float(parts[1]), 4)
    except Exception:
        pass
    return 0.8800

def fetch_from_eastmoney(symbol, is_hk):
    """从东方财富 push2 接口获取单股估值与行情"""
    secid = f"116.{symbol.zfill(5)}" if is_hk else (f"1.{symbol}" if symbol.startswith(('6', '9')) else f"0.{symbol}")
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f57,f58,f116,f162,f163,f164,f167,f169,f170"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://quote.eastmoney.com/'
    }
    r = requests.get(url, headers=headers, timeout=4)
    if r.status_code == 200:
        d = r.json().get('data')
        if d and d.get('f58') and d.get('f58') != '-':
            price = (d['f43'] / 1000.0 if is_hk else d['f43'] / 100.0) if d.get('f43') else None
            pe_ttm = d['f164'] / 100.0 if d.get('f164') and d['f164'] != '-' else None
            pb = d['f167'] / 100.0 if d.get('f167') and d['f167'] != '-' else None
            mkt_cap = d.get('f116') / 1e8 if d.get('f116') else None
            change_pct = d.get('f170') / 100.0 if d.get('f170') and d['f170'] != '-' else None
            return {
                'source': 'Eastmoney',
                'code': d.get('f57'),
                'name': d.get('f58'),
                'price': price,
                'market_cap_raw': mkt_cap,
                'pe_ttm': pe_ttm,
                'pb': pb,
                'change_pct': change_pct
            }
    return None

def fetch_from_tencent(symbol, is_hk):
    """从腾讯财经接口获取单股估值与行情（备用降级）"""
    t_sym = f"r_hk{symbol.zfill(5)}" if is_hk else (("sh" if symbol.startswith("6") else "sz") + symbol)
    r = requests.get(f"https://qt.gtimg.cn/q={t_sym}", timeout=4)
    if r.status_code == 200 and '~' in r.text:
        parts = r.text.split('~')
        if len(parts) > 45:
            name = parts[1]
            code = parts[2]
            price = float(parts[3]) if parts[3] else None
            mkt_cap = float(parts[45]) if parts[45] else None
            change_pct = float(parts[32]) if len(parts) > 32 and parts[32] else None
            if is_hk:
                pe_ttm = float(parts[57]) if len(parts) > 57 and parts[57] and parts[57] != '0' else None
                pb = float(parts[58]) if len(parts) > 58 and parts[58] and parts[58] != '0' else None
            else:
                pe_ttm = float(parts[53]) if len(parts) > 53 and parts[53] and parts[53] != '0' else None
                pb = float(parts[46]) if len(parts) > 46 and parts[46] and parts[46] != '0' else None
            return {
                'source': 'Tencent',
                'code': code,
                'name': name,
                'price': price,
                'market_cap_raw': mkt_cap,
                'pe_ttm': pe_ttm,
                'pb': pb,
                'change_pct': change_pct
            }
    return None

def fetch_pe_percentile_baidu(symbol, is_hk, current_pe=None, period='全部'):
    """直接调用百度股市通接口获取官方历史 PE(TTM) 序列并计算分位数"""
    try:
        market = 'hk' if is_hk else 'ab'
        params = {
            'openapi': '1',
            'dspName': 'iphone',
            'tn': 'tangram',
            'client': 'app',
            'query': '市盈率(TTM)',
            'code': symbol.zfill(5) if is_hk else symbol,
            'word': '',
            'resource_id': '51171',
            'market': market,
            'tag': '市盈率(TTM)',
            'chart_select': period,
            'skip_industry': '1',
            'finClientType': 'pc',
        }
        url = f"https://gushitong.baidu.com/opendata?{urllib.parse.urlencode(params)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            chart_info = data['Result'][0]['DisplayData']['resultData']['tplData']['result']['chartInfo'][0]
            body = chart_info.get('body', [])
            if body:
                pe_series = [float(item[1]) for item in body if len(item) > 1 and item[1] and float(item[1]) > 0]
                if pe_series:
                    target_pe = current_pe if current_pe is not None else pe_series[-1]
                    days_below = sum(1 for p in pe_series if p < target_pe)
                    total_days = len(pe_series)
                    percentile = round((days_below / total_days) * 100, 2)
                    sorted_pe = sorted(pe_series)
                    median_pe = round(sorted_pe[total_days // 2], 2)
                    min_pe = round(sorted_pe[0], 2)
                    max_pe = round(sorted_pe[-1], 2)
                    return {
                        'status': 'success',
                        'percentile': percentile,
                        'period': period,
                        'days_below': days_below,
                        'total_days': total_days,
                        'min_pe': min_pe,
                        'max_pe': max_pe,
                        'median_pe': median_pe,
                        'source': 'Baidu Stock'
                    }
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
    return {'status': 'failed', 'error': '未获取到历史估值数据'}

def fetch_stock_valuation(symbol):
    sym = str(symbol).strip()
    is_hk = len(sym) == 5 or (len(sym) < 5 and sym.isdigit())
    
    # 1. 获取实时行情与PE点值 (优先东财，降级腾讯)
    data = None
    try:
        data = fetch_from_eastmoney(sym, is_hk)
    except Exception:
        pass
        
    if not data or not data.get('pe_ttm'):
        try:
            data = fetch_from_tencent(sym, is_hk)
        except Exception:
            pass
            
    if not data:
        return {'error': f'未能获取到股票 {symbol} 的行情数据'}

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['timestamp'] = now_str
    
    # 汇率处理
    if is_hk:
        fx = get_hkd_cny_rate()
        data['currency'] = 'HKD'
        data['market_cap_hkd'] = data['market_cap_raw']
        data['market_cap_cny'] = round(data['market_cap_raw'] * fx, 2) if data['market_cap_raw'] else None
        data['hkd_cny_rate'] = fx
    else:
        data['currency'] = 'CNY'
        data['market_cap_cny'] = data['market_cap_raw']

    # 2. 直接调用成熟财经接口获取历史 PE 分位数
    pct_info = fetch_pe_percentile_baidu(sym, is_hk, current_pe=data.get('pe_ttm'), period='全部')
    data['pe_percentile'] = pct_info
        
    return data

def main():
    parser = argparse.ArgumentParser(description='获取单只 A 股或港股的实时估值及权威历史分位数')
    parser.add_argument('symbol', type=str, help='股票代码，例如 09633、000333、600809')
    parser.add_argument('--json', action='store_true', help='输出纯 JSON 格式')
    args = parser.parse_args()

    result = fetch_stock_valuation(args.symbol)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if 'error' in result:
        print(f"❌ 错误: {result['error']}")
        sys.exit(1)

    print("=" * 60)
    print(f"📊 {result['name']} ({result['code']}) 实时估值与分位看板")
    print(f"⏰ 查询时间: {result['timestamp']} (实时源: {result['source']})")
    print("=" * 60)
    print(f"现价:          {result['price']} {result['currency']} ({result.get('change_pct', 0):+.2f}%)")
    if result.get('currency') == 'HKD':
        print(f"总市值:        {result['market_cap_hkd']:.2f} 亿港元 (≈ {result['market_cap_cny']:.2f} 亿人民币)")
        print(f"实时汇率:      1 HKD = {result['hkd_cny_rate']} CNY")
    else:
        print(f"总市值:        {result['market_cap_cny']:.2f} 亿元")
    print(f"PE (TTM):      {result['pe_ttm']}x")
    print(f"PB (市净率):   {result['pb']}x")

    pct = result.get('pe_percentile')
    if pct and pct.get('status') == 'success':
        print("-" * 60)
        print(f"🎯 PE 历史分位: {pct['percentile']}% ({pct['period']} {pct['total_days']} 个交易日，仅 {pct['days_below']} 天更低)")
        print(f"📈 估值区间:    中位数 {pct['median_pe']}x | 最低 {pct['min_pe']}x | 最高 {pct['max_pe']}x")
        print(f"🏛️ 历史源:      {pct['source']} 官方历史序列")
    print("=" * 60)
    print("💡 校验提示：PE(TTM) 与分位数均直连成熟财经官方接口，严禁手工估算篡改。")

if __name__ == '__main__':
    main()
