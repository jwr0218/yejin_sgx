import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from dateutil.relativedelta import relativedelta

import config
from request.request_other import get_year_prices
from screenshot import take_screenshot

class Page2(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.table = QTableWidget(0, 5)
        headers = ["Item", "yday", "tday", "+/-", "usd+/-"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setStyleSheet(config.HEADER_STYLE)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("데이터 불러오기")
        self.btn_load.clicked.connect(self.load_all_market_data)
        
        self.btn_capture = QPushButton("화면 캡처 (Save Image)")
        self.btn_capture.clicked.connect(lambda: take_screenshot(self, "Page2"))
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_capture)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_target_months(self):
        """
        현재 달 기준 향후 13개월을 탐색하여 Main(1,3,5,9) 및 근월물(+1, +2) 추출
        2월일 경우 내년 1월물까지 포함되도록 i 범위를 13으로 설정
        """
        # 실험용: 2월 상황을 보고 싶다면 아래 주석을 해제하세요.
        # now = datetime.datetime(2026, 2, 1) 
        now = datetime.datetime.now()
        
        main_months = {1, 3, 5, 9}
        valid_targets = []
        
        # 0(현재달)부터 12(내년 이맘때)까지 총 13개월 탐색
        for i in range(13):
            check_date = now + relativedelta(months=i)
            y, m = check_date.year, check_date.month
            
            is_main = m in main_months
            is_near = i <= 2 # 현재달, 다음달, 다다음달
            
            if is_main or is_near:
                # 중복 체크 (연도까지 고려)
                if not any(t['year'] == y and t['month'] == m for t in valid_targets):
                    valid_targets.append({"year": y, "month": m})
        
        # 연도와 월 순서로 정렬
        valid_targets.sort(key=lambda x: (x['year'], x['month']))
        return valid_targets

    def load_all_market_data(self):
        """데이터 로드 및 테이블 출력"""
        pta_t_raw = get_year_prices("nf_TA", 8)
        pta_y_raw = get_year_prices("nf_TA", 10)
        px_t_raw = get_year_prices("nf_PX", 8)
        px_y_raw = get_year_prices("nf_PX", 10)

        def merge_data(t_list, y_list):
            merged = {}
            # API 반환 형식이 'YYYY/MM' 또는 'YY/MM'일 경우를 대비
            for t, y in zip(t_list, y_list):
                if t['price'] != "N/A" and y['price'] != "N/A":
                    # key format: (year_2digit, month)
                    parts = t['month'].split('/')
                    y_val = int(parts[0]) % 100 # 뒤 2자리 연도
                    m_val = int(parts[1])
                    merged[(y_val, m_val)] = {'tday': float(t['price']), 'yday': float(y['price'])}
            return merged

        pta_data = merge_data(pta_t_raw, pta_y_raw)
        px_data = merge_data(px_t_raw, px_y_raw)

        self.table.setRowCount(0)
        
        # 타겟 월물 리스트 가져오기
        target_list = self.get_target_months()

        # 제품별 행 추가
        self.add_product_rows("PTA", pta_data, target_list)
        self.add_product_rows("PX", px_data, target_list)
        
        self.table.resizeColumnsToContents()

    def add_product_rows(self, name, data_dict, target_list):
        """동적 타겟 리스트를 기반으로 행 추가 (형식: 26-JAN)"""
        active_info = {} 

        # 1. 월물별 데이터 출력
        for t in target_list:
            yy = t['year'] % 100  # 2026 -> 26
            mm = t['month']
            
            if (yy, mm) in data_dict:
                info = data_dict[(yy, mm)]
                active_info[mm] = info 
                
                # 라벨 형식을 YY-MONTH (예: PTA 26-JAN) 로 변경
                label = f"{name} {yy}-{self._month_name(mm)}"
                self._insert_row(label, info['yday'], info['tday'])

        # 2. 스프레드 항목 추가 (데이터가 존재하는 경우에만)
        spread_targets = [
            {"label": "1/2", "m1": 1, "m2": 2},
            {"label": "1/3", "m1": 1, "m2": 3},
            {"label": "3/5", "m1": 3, "m2": 5},
            {"label": "1/5", "m1": 1, "m2": 5},
            {"label": "5/9", "m1": 5, "m2": 9}
        ]
        
        for s in spread_targets:
            m1, m2 = s["m1"], s["m2"]
            if m1 in active_info and m2 in active_info:
                v1, v2 = active_info[m1], active_info[m2]
                s_yday = v1['yday'] - v2['yday']
                s_tday = v1['tday'] - v2['tday']
                
                # 스프레드 이름 (예: PTA 1/2)
                self._insert_row(f"{name} {s['label']}", s_yday, s_tday)

    def _insert_row(self, label, yday, tday):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Item 이름
        item_label = QTableWidgetItem(label)
        item_label.setBackground(QColor("#D9EAD3"))
        self.table.setItem(row, 0, item_label)
        
        # yday, tday
        self.table.setItem(row, 1, QTableWidgetItem(f"{yday:,.2f}"))
        self.table.setItem(row, 2, QTableWidgetItem(f"{tday:,.2f}"))
        
        # +/-
        diff = tday - yday
        diff_item = QTableWidgetItem(f"{diff:+.2f}")
        if diff > 0: diff_item.setForeground(QColor("red"))
        elif diff < 0: diff_item.setForeground(QColor("blue"))
        self.table.setItem(row, 3, diff_item)

        # usd+/-
        usd_diff = diff / 7.2
        usd_item = QTableWidgetItem(f"{usd_diff:+.2f}")
        if usd_diff > 0: usd_item.setForeground(QColor("red"))
        elif usd_diff < 0: usd_item.setForeground(QColor("blue"))
        self.table.setItem(row, 4, usd_item)

        for i in range(5):
            it = self.table.item(row, i)
            if it: it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def _month_name(self, m):
        return ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"][m]