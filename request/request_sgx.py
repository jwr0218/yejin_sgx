import urllib.request
import urllib.error
import socket
import ssl
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


# 마지막 조회가 실패했을 때의 사유. 화면에서 실패 원인을 보여 주는 데 쓴다.
last_error = None


def describe_error(e):
    """요청 예외를 사용자가 원인을 짐작할 수 있는 문장으로 바꾼다. 원문도 함께 붙인다."""
    if isinstance(e, urllib.error.HTTPError):
        if e.code == 403:
            why = "SGX 서버가 접속을 거부했습니다(403). 현재 네트워크/IP가 SGX에 의해 차단된 것으로 보입니다."
        elif e.code == 429:
            why = "요청이 너무 잦아 SGX가 일시적으로 막았습니다(429). 잠시 후 다시 시도해 주세요."
        elif e.code >= 500:
            why = f"SGX 서버 오류입니다({e.code}). 잠시 후 다시 시도해 주세요."
        else:
            why = f"SGX 서버가 오류 코드 {e.code}를 돌려주었습니다."
    else:
        reason = getattr(e, 'reason', e)
        if isinstance(reason, ssl.SSLError) or 'CERTIFICATE' in str(e).upper():
            why = "SSL 인증서 확인에 실패했습니다. 회사 보안 장비/프록시가 HTTPS를 가로채는 환경일 수 있습니다."
        elif isinstance(reason, (socket.timeout, TimeoutError)) or 'timed out' in str(e):
            why = "SGX 서버 응답 시간이 초과되었습니다. 네트워크가 느리거나 방화벽에서 막혀 있을 수 있습니다."
        elif isinstance(reason, socket.gaierror):
            why = "api.sgx.com 주소를 찾지 못했습니다. 인터넷 연결 또는 DNS/프록시 설정을 확인해 주세요."
        elif isinstance(reason, (ConnectionRefusedError, ConnectionResetError)):
            why = "SGX 서버와의 연결이 거부/끊겼습니다. 방화벽이나 프록시에서 막혀 있을 수 있습니다."
        elif isinstance(e, json.JSONDecodeError):
            why = "SGX 응답 형식이 예상과 다릅니다(차단 안내 페이지 등이 돌아왔을 수 있습니다)."
        else:
            why = "SGX 서버에 접속하지 못했습니다."
    return f"{why}\n\n(상세: {type(e).__name__}: {e})"


def _fetch(retries=2):
    t = int(time.time() * 1000)
    req = urllib.request.Request(_SGX_API.format(t=t), headers=_HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f"SGX API 요청 실패 ({attempt + 1}/{retries}): {e}")
            if attempt + 1 == retries:
                raise
            time.sleep(1)


def get_year_sgx():
    global last_error
    print("--- SGX 정보 추출 시작 ---")
    last_error = None
    try:
        data = _fetch()
    except Exception as e:
        last_error = describe_error(e)
        return [{"month": "N/A", "price": "N/A"} for _ in range(MONTHS_AHEAD)]

    # 월물마다 T 세션(0)과 T+1 세션(1) 행이 따로 온다 (응답은 delivery-month 오름차순).
    by_delivery = {}
    for item in data.get('data', []):
        by_delivery.setdefault(item.get('delivery-month', ''), []).append(item)

    results = []
    for delivery, rows in by_delivery.items():  # "2026-05"
        # Sina API와 동일한 "YY/MM" 형식으로 변환
        try:
            yy, mm = delivery.split('-')
            month = f"{yy[2:]}/{mm}"  # "26/05"
        except Exception:
            month = delivery

        # 지금 거래 중인 가격을 보이도록, 두 세션 중 가장 최근에 체결된 쪽을 쓴다.
        # (T 세션만 보면 야간 T+1 세션 동안 낮의 마지막 체결가에 머문다)
        traded = [r for r in rows if r.get('last-traded-price-adj') is not None]
        latest = max(traded, key=lambda r: r.get('last-update-time') or '', default=None)
        if latest:
            price = str(latest['last-traded-price-adj'])
            # "2026-10-14 14:13:52.0" -> "2026-10-14 14:13:52" (싱가포르 시간)
            traded_at = (latest.get('last-update-time') or '').split('.')[0]
        else:
            price, traded_at = 'N/A', ''

        print(f"  month={month}, price={price}, time={traded_at}")
        results.append({"month": month, "price": price, "time": traded_at})

        if len(results) >= MONTHS_AHEAD:
            break

    if not results:
        last_error = "SGX 응답은 받았지만 시세 데이터가 비어 있습니다."
    elif all(r['price'] == 'N/A' for r in results):
        last_error = ("SGX 응답은 받았지만 모든 월물에 체결가가 없습니다. "
                      "장 시작 전이거나 SGX 데이터 갱신 중일 수 있습니다. 잠시 후 다시 로드해 주세요.")

    # MONTHS_AHEAD 미만이면 N/A로 채움
    while len(results) < MONTHS_AHEAD:
        results.append({"month": "N/A", "price": "N/A"})

    return results


if __name__ == '__main__':
    print(get_year_sgx())
