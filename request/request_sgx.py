from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import sys
import os
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import platform

_driver = None


def get_driver():
    global _driver
    if _driver is not None:
        return _driver

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--lang=ko_KR')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')

    try:
        # 방법 1: webdriver-manager로 자동 다운로드
        driver_path = ChromeDriverManager().install()
        driver_dir = os.path.dirname(driver_path)
        is_win = platform.system() == "Windows"
        driver_name = "chromedriver.exe" if is_win else "chromedriver"
        service = Service(os.path.join(driver_dir, driver_name))
        _driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        # 방법 2: 실패하면 Selenium 내장 매니저로 시도
        _driver = webdriver.Chrome(options=options)

    _driver.get('https://www.sgx.com/derivatives/delayed-prices-futures?category=fx&cc=UC')
    _driver.implicitly_wait(5)
    time.sleep(5)
    return _driver


def get_year_sgx():
    """
    SGX USD/CNH 데이터를 추출하며, 동적 로딩 대기 및 예외 처리를 포함합니다.
    Input/Output 포맷은 이전과 동일하게 유지됩니다.
    """
    print("--- SGX 정보 추출 시작 ---")
    driver = get_driver()  # 첫 호출 시 생성, 이후 재사용


    current_date = datetime.now()
    months_info = []
    results = []

    # 1. 12개월 라벨 미리 생성
    for i in range(12):
        target_date = current_date + relativedelta(months=i)
        months_info.append(target_date.strftime("%y/%m"))

    # 2. 첫 번째 요소가 나타날 때까지 명시적 대기 (최대 15초)
    # 테이블 자체가 로드되지 않았을 때를 대비한 안전장치입니다.
    try:
        first_xpath = '//*[@id="page-container"]/template-base/div/div/sgx-widgets-wrapper/widget-derivatives-futures-prices/section[1]/div[1]/sgx-table/div/sgx-table-list/sgx-table-row[1]'
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, first_xpath)))
    except Exception as e:
        print(f"테이블 로딩 시간 초과: {e}")
        return [{"month": m, "price": "N/A"} for m in months_info]

    # 3. 데이터 추출 루프
    for i in range(12):
        idx = (i * 2) + 1
        xpath = f'//*[@id="page-container"]/template-base/div/div/sgx-widgets-wrapper/widget-derivatives-futures-prices/section[1]/div[1]/sgx-table/div/sgx-table-list/sgx-table-row[{idx}]/sgx-table-cell-number[1]'
        
        try:
            # 개별 요소 탐색 (암시적 대기 활용)
            target = driver.find_element(By.XPATH, xpath)
            
            # .text가 비어있는 경우가 많으므로 textContent를 우선순위로 가져옴
            value = target.get_attribute('textContent').strip() or target.text.strip()

            # 특수 문자 '﹣' (Full-width hyphen) 및 빈 값 처리
            if value in ['﹣', '', '-', 'None']:
                results.append({"month": months_info[i], "price": "N/A"})
            else:
                results.append({"month": months_info[i], "price": value})
                
        except Exception:
            # 요소를 찾지 못할 경우에도 리스트 길이를 맞추기 위해 N/A 삽입
            results.append({"month": months_info[i], "price": "N/A"})

    return results

def turn_off_driver():
    print('프로그램 종료, driver를 종료합니다.')
    driver.quit()



def turn_off_driver():
    global _driver
    print('프로그램 종료, driver를 종료합니다.')
    if _driver:
        _driver.quit()
        _driver = None


if __name__ == '__main__':
    print(get_year_sgx())
    turn_off_driver()