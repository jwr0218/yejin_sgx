import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

def get_year_prices(base_symbol_prefix, price_index):
    """
    base_symbol_prefix: 'nf_TA' (PTA), 'nf_PX' (PX) 등
    price_index: 데이터에서 현재가가 위치한 인덱스 (PTA/PX는 8번, Brent는 0번 등)
    price_index : 전날 종가? 
    """
    current_date = datetime.now()
    months_info = []
    symbols = []

    # 1. 지금부터 12개월간의 심볼 생성
    for i in range(12):
        target_date = current_date + relativedelta(months=i)
        yy = target_date.strftime("%y") # '26'
        mm = target_date.strftime("%m") # '05'
        
        symbol = f"{base_symbol_prefix}{yy}{mm}"
        symbols.append(symbol)
        months_info.append(f"{yy}/{mm}")

    # 2. API 호출 (콤마로 심볼 결합)
    api_url = f"https://hq.sinajs.cn/list={','.join(symbols)}"
    headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(api_url, headers=headers)
        lines = response.text.strip().split('\n')
        
        results = []
        for i, line in enumerate(lines):
            if '"' in line:
                content = line.split('"')[1]
                if not content: # 데이터가 없는 월물인 경우
                    results.append({"month": months_info[i], "price": "N/A"})
                    continue
                
                data_list = content.split(',')
                # 현재가 추출 (PTA/PX 등 내수선물은 8번이 현재가임)
                price = data_list[price_index]
                results.append({"month": months_info[i], "price": price})
        
        return results

    except Exception as e:
        print(f"Error: {e}")
        return []



if __name__ == '__main__':
        
    # --- 실행 예시 ---
    # PTA (내수선물 nf_TA, 현재가 인덱스 8)
    pta_year_data = get_year_prices("nf_TA", 8)

    print("--- 1년치 오늘자 PTA 가격 리스트 ---")
    for item in pta_year_data:
        print(f"{item['month']} : {item['price']}")

    pta_year_data = get_year_prices("nf_TA", 10)
    print("--- 1년치 어제자 PTA 가격 리스트 ---")
    for item in pta_year_data:
        print(f"{item['month']} : {item['price']}")


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
