import requests
import re
import json
import concurrent.futures
from datetime import datetime
from dateutil.relativedelta import relativedelta

_KLINE_URL = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_x=/InnerFuturesNewService.getDailyKLine?symbol={symbol}"
_HEADERS = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}

# 조회할 월물 개수(당월 포함). 거래소가 12개월 연속 월물을 상장하므로 당월부터
# 12개만 세면 이미 상장된 마지막 월물이 잘린다. 한 달 여유를 둔다.
MONTHS_AHEAD = 13

# 실시간 시세 응답에서 '시세 일자'가 놓인 인덱스는 심볼 종류마다 다르다.
#   nf_ (정저우/다롄 등 내수 선물) : 필드 44개, 17번이 일자
#   hf_ (브렌트유 등 외방 선물)    : 필드 15개, 12번이 일자
_QUOTE_DATE_INDEX = {"nf_": 17, "hf_": 12}
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _quote_date_index(base_symbol_prefix):
    for prefix, index in _QUOTE_DATE_INDEX.items():
        if base_symbol_prefix.startswith(prefix):
            return index
    return None


def _fetch_prev_close(session, yy, mm, symbol):
    try:
        resp = session.get(_KLINE_URL.format(symbol=symbol), headers=_HEADERS, timeout=10)
        match = re.search(r'\((\[.*\]|null)\)', resp.text)
        if not match or match.group(1) == 'null':
            return (yy, mm), None

        bars = json.loads(match.group(1))
        if len(bars) == 0:
            return (yy, mm), None

        today_str = datetime.now().strftime("%Y-%m-%d")

        # 마지막 봉이 오늘 날짜면 그 이전 봉이 '전일 종가', 아직 오늘 봉이 없으면
        # 마지막 봉 자체가 '전일(=가장 최근 완료된 거래일) 종가'가 된다.
        if bars[-1]['d'] == today_str:
            prev_close = float(bars[-2]['c']) if len(bars) >= 2 else None
        else:
            prev_close = float(bars[-1]['c'])

        return (yy, mm), prev_close
    except Exception as e:
        print(f"K-line Error ({symbol}): {e}")
        return (yy, mm), None


def get_year_prev_close(product_code, months=MONTHS_AHEAD):
    """
    product_code: 'TA'(PTA), 'PX' 등 (내수 선물 심볼, 'nf_' 접두어 제외)

    실시간 시세(hq.sinajs.cn)의 인덱스 10은 '전일 결제가'라서 실제 '전일 종가'와 다름.
    일별 K차트(getDailyKLine)는 날짜별 종가(c)가 명확히 구분되므로,
    월물별로 '오늘 이전 마지막 거래일'의 종가만 정확히 가져온다.
    (오늘의 실시간 거래가는 get_year_prices로 별도 조회)

    월물별로 요청이 각각 필요해 순차 호출하면 느리므로,
    스레드풀로 동시에 요청해 응답 시간을 단축한다.
    """
    current_date = datetime.now()
    targets = []
    for i in range(months):
        target_date = current_date + relativedelta(months=i)
        yy = int(target_date.strftime("%y"))
        mm = int(target_date.strftime("%m"))
        targets.append((yy, mm, f"{product_code}{yy:02d}{mm:02d}"))

    results = {}
    with requests.Session() as session, \
         concurrent.futures.ThreadPoolExecutor(max_workers=len(targets)) as executor:
        futures = [executor.submit(_fetch_prev_close, session, yy, mm, symbol) for yy, mm, symbol in targets]
        for future in concurrent.futures.as_completed(futures):
            key, value = future.result()
            results[key] = value

    return results


def get_year_prices(base_symbol_prefix, price_index):
    """
    base_symbol_prefix: 'nf_TA' (PTA), 'nf_PX' (PX) 등
    price_index: 데이터에서 현재가가 위치한 인덱스 (PTA/PX는 8번, Brent는 0번 등)
    price_index : 전날 종가?

    반환값의 각 항목은 아래 키를 가진다.
        month : 'YY/MM'
        price : 현재가 문자열 (없으면 'N/A')
        date  : 그 월물의 마지막 시세 일자 ('YYYY-MM-DD', 못 읽으면 None)
        stale : 만기 등으로 거래가 멈춰 date가 최신 장 일자보다 과거인 경우 True

    만기가 지난 월물도 sina는 마지막 체결가를 계속 돌려주기 때문에,
    값만 보면 실시간 시세와 구분되지 않는다. 응답에 함께 오는 시세 일자를
    같이 넘겨 화면에서 구분할 수 있게 한다.
    """
    current_date = datetime.now()
    months_info = []
    symbols = []

    # 1. 지금부터 MONTHS_AHEAD 개월간의 심볼 생성
    for i in range(MONTHS_AHEAD):
        target_date = current_date + relativedelta(months=i)
        yy = target_date.strftime("%y") # '26'
        mm = target_date.strftime("%m") # '05'
        
        symbol = f"{base_symbol_prefix}{yy}{mm}"
        symbols.append(symbol)
        months_info.append(f"{yy}/{mm}")

    # 2. API 호출 (콤마로 심볼 결합)
    api_url = f"https://hq.sinajs.cn/list={','.join(symbols)}"
    headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    
    date_index = _quote_date_index(base_symbol_prefix)

    try:
        response = requests.get(api_url, headers=headers)
        lines = response.text.strip().split('\n')

        results = []
        for i, line in enumerate(lines):
            if '"' in line:
                content = line.split('"')[1]
                if not content: # 데이터가 없는 월물인 경우
                    results.append({"month": months_info[i], "price": "N/A", "date": None, "stale": False})
                    continue

                data_list = content.split(',')
                # 현재가 추출 (PTA/PX 등 내수선물은 8번이 현재가임)
                price = data_list[price_index]

                quote_date = None
                if date_index is not None and date_index < len(data_list):
                    raw_date = data_list[date_index].strip()
                    if _DATE_RE.match(raw_date):
                        quote_date = raw_date

                results.append({"month": months_info[i], "price": price,
                                "date": quote_date, "stale": False})

        # 같은 상품의 월물들 중 가장 최근 시세 일자를 '현재 장 일자'로 보고,
        # 그보다 과거에 멈춰 있는 월물을 거래 정지로 표시한다.
        # (휴장일에는 전 월물이 같은 날짜라 아무것도 표시되지 않는다 - 의도된 동작)
        quote_dates = [r["date"] for r in results if r["date"]]
        if quote_dates:
            latest = max(quote_dates)
            for r in results:
                if r["date"] and r["date"] < latest:
                    r["stale"] = True

        return results

    except Exception as e:
        print(f"Error: {e}")
        return []



if __name__ == '__main__':

    headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}

    for symbol in ["nf_TA2605", "nf_PX2605"]:
        url = f"https://hq.sinajs.cn/list={symbol}"
        r = requests.get(url, headers=headers)
        content = r.text.split('"')[1]
        print(f"--- {symbol} 원본 응답 ---")
        for i, v in enumerate(content.split(',')):
            print(f"[{i}] {v}")
        print()


    exit()
    # --- 실행 예시 ---
    pta_year_data = get_year_prices("nf_PX", 8)
    

    print("--- 1년치 PX 가격 리스트 ---")
    for item in pta_year_data:
        print(f"{item['month']} : {item['price']}")


    # --- 실행 예시 ---
    pta_year_data = get_year_prices("hf_OIL", 8)

    print("--- 1년치 BRENT OIL 가격 리스트 ---")
    for item in pta_year_data:
        print(f"{item['month']} : {item['price']}")
