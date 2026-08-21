import urllib.request
import json
import time


# sina 쪽(request_other.MONTHS_AHEAD)과 조회 구간을 맞춘다.
MONTHS_AHEAD = 14

_SGX_API = 'https://api.sgx.com/derivatives/v1.0/contract-code/UC?order=asc&orderby=delivery-month&category=futures&session=-1&t={t}'
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.sgx.com/derivatives/delayed-prices-futures?category=fx&cc=UC',
    'Origin': 'https://www.sgx.com',
}


def get_year_sgx():
    print("--- SGX 정보 추출 시작 ---")
    t = int(time.time() * 1000)
    url = _SGX_API.format(t=t)
    req = urllib.request.Request(url, headers=_HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"SGX API 요청 실패: {e}")
        return [{"month": "N/A", "price": "N/A"} for _ in range(MONTHS_AHEAD)]

    results = []
    for item in data.get('data', []):
        if item.get('current-trading-session') != '0':
            continue

        delivery = item.get('delivery-month', '')  # "2026-05"
        # Sina API와 동일한 "YY/MM" 형식으로 변환
        try:
            yy, mm = delivery.split('-')
            month = f"{yy[2:]}/{mm}"  # "26/05"
        except Exception:
            month = delivery

        price_val = item.get('last-traded-price-adj')
        price = 'N/A' if price_val is None else str(price_val)

        print(f"  month={month}, price={price}")
        results.append({"month": month, "price": price})

        if len(results) >= MONTHS_AHEAD:
            break

    # MONTHS_AHEAD 미만이면 N/A로 채움
    while len(results) < MONTHS_AHEAD:
        results.append({"month": "N/A", "price": "N/A"})

    return results


if __name__ == '__main__':
    print(get_year_sgx())
