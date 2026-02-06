import datetime
import csv
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt , QTimer
from dateutil.relativedelta import relativedelta

import config
from request.request_other import get_year_prices 
from request.request_sgx import get_year_sgx
from screenshot import take_screenshot

class Page1(QWidget):
    def __init__(self):
        super().__init__()
        self.CONST_PX_PTA = 0.655 * 1.13 * 1.02
        self.CONST_ZCE_SGX = 1.13 * 1.02
        
        layout = QVBoxLayout()

        self.headers = [
            "Month", "BRENT", "Mopj", "MOPJ SPREAD", "PX", 
            "PX SPREAD", "PXN", "PX Futures", "PTA Futures", 
            "PX-PTA SPREAD", "ZCEPX-SGXPX", "USD/CNH", "BOX"
        ]
        
        self.table = QTableWidget(12, len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        
        # UI 초기화 및 스타일 적용
        self.init_table_defaults()
        self.init_month_labels() # 강조 로직 포함
        
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("Market 데이터 로드")
        self.btn_load.clicked.connect(self.load_all_market_data)
        
        self.btn_reset = QPushButton("모든 값 초기화")
        self.btn_reset.clicked.connect(self.reset_all_data)
        
        self.btn_excel = QPushButton("엑셀(CSV) 생성")
        self.btn_excel.clicked.connect(self.export_to_csv)
        
        self.btn_capture = QPushButton("화면 캡처")
        self.btn_capture.clicked.connect(lambda: take_screenshot(self, "Page1"))
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_excel)
        btn_layout.addWidget(self.btn_capture)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def init_table_defaults(self):
        for row in range(12):
            for col in [3, 5]: 
                self.set_val(row, col, 0)

    def init_month_labels(self):
        """날짜 형식 수정(26-JAN) 및 행별 강조(Bold/Color) 적용"""
        now = datetime.datetime.now()
        bold_font = QFont()
        bold_font.setBold(True)
        
        # 강조할 월 리스트 (숫자 기준)
        bold_months = [1, 3, 5, 7, 9, 11]
        color_months = [1, 5, 9]

        for i in range(12):
            target_date = now + relativedelta(months=i)
            month_int = target_date.month
            
            # 1. 날짜 형식 수정: 26-JAN
            month_str = target_date.strftime("%y-%b").upper()
            item = QTableWidgetItem(month_str)
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, item)

            # 2. 월별 강조 로직
            # 홀수 달 볼드 처리
            if month_int in bold_months:
                for col in range(len(self.headers)):
                    if not self.table.item(i, col):
                        self.table.setItem(i, col, QTableWidgetItem(""))
                    self.table.item(i, col).setFont(bold_font)
            
            # 1, 5, 9월 색상 강조 (연한 파랑/하늘색)
            if month_int in color_months:
                for col in range(len(self.headers)):
                    if not self.table.item(i, col):
                        self.table.setItem(i, col, QTableWidgetItem(""))
                    self.table.item(i, col).setBackground(QColor("#D9EAD3"))

    def set_val(self, row, col, val, precision=2, is_editable=True):
        """특정 컬럼(PX/PTA Futures)에 대해 소수점 제거 적용"""
        self.table.blockSignals(True)
        
        # PX Futures(7)와 PTA Futures(8)는 소수점 0자리 적용
        if col in [7, 8]:
            precision = 0
            
        item = self.table.item(row, col)
        if not item:
            item = QTableWidgetItem()
            self.table.setItem(row, col, item)
        
        item.setText(f"{val:,.{precision}f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if not is_editable:
            item.setBackground(QColor("#F0F4F8"))
        self.table.blockSignals(False)

    def on_item_changed(self, item):
        col = item.column()
        if col in [1, 2, 3, 4, 5, 7, 8, 11]:
            self.calculate_all_logic()

    def calculate_all_logic(self):
        """계단식 로직 및 수식 계산"""
        for row in range(12):
            if row > 0:
                self.set_val(row, 2, self.get_val(row-1, 2) - self.get_val(row-1, 3)) 
                self.set_val(row, 4, self.get_val(row-1, 4) - self.get_val(row-1, 5)) 

            mopj = self.get_val(row, 2)
            px = self.get_val(row, 4)
            px_future = self.get_val(row, 7)
            pta_future = self.get_val(row, 8)
            usd_cnh = self.get_val(row, 11)

            self.set_val(row, 6, px - mopj)
            self.set_val(row, 9, pta_future - (self.CONST_PX_PTA * px * usd_cnh))
            self.set_val(row, 10, px_future - (px * self.CONST_ZCE_SGX * usd_cnh))

        for row in range(11):
            self.set_val(row, 12, self.get_val(row, 6) - self.get_val(row+1, 6))

    def get_val(self, row, col):
        if row < 0 or row >= 12: return 0.0
        item = self.table.item(row, col)
        if not item or not item.text() or item.text() == "N/A": return 0.0
        try:
            return float(item.text().replace(',', ''))
        except ValueError:
            return 0.0

    def load_all_market_data(self):
        """API 로드 및 2-Pass 보정 (앞 칸 우선 채우기 -> 남은 빈칸 뒷 칸 채우기)"""
        self.table.blockSignals(True)
        
        # 1. API 데이터 기본 로드 (기존 소스 동일)
        pta_data = get_year_prices("nf_TA", 8)
        px_future_data = get_year_prices("nf_PX", 8)
        brent_oil = get_year_prices("hf_OIL", 8)
        sgx_value = get_year_sgx()

        for row in range(12):
            if row < len(brent_oil) and brent_oil[row]['price'] != 'N/A':
                self.set_val(row, 1, float(brent_oil[row]['price']))
            if row < len(px_future_data) and px_future_data[row]['price'] != 'N/A':
                self.set_val(row, 7, float(px_future_data[row]['price']))
            if row < len(pta_data) and pta_data[row]['price'] != 'N/A':
                self.set_val(row, 8, float(pta_data[row]['price']))
            
            if row < len(sgx_value) and sgx_value[row]['price'] != 'N/A':
                self.set_val(row, 11, float(sgx_value[row]['price']))
                item = self.table.item(row, 11)
                if item: item.setForeground(QColor("black"))
            else:
                self.set_val(row, 11, 0)

        # 2. [Pass 1] 순방향 보정: 앞 칸(위)의 값을 아래로 전파 (앞 칸 우선 논리)
        check = [False for i in range(1,13)]

        for row in range(1, 12): # 1번 행부터 시작
            if self.get_val(row, 11) == 0 :
                prev_v = self.get_val(row - 1, 11)
                if prev_v != 0 and check[row-1] == False:
                    check[row] = True
                    self.set_val(row, 11, prev_v)
                    item = self.table.item(row, 11)
                    if item: item.setForeground(QColor("blue"))

        # 3. [Pass 2] 역방향 보정: 여전히 0인 칸은 뒷 칸(아래)의 값을 위로 전파
        for row in range(10, -1, -1): # 10번 행부터 0번 행까지 거꾸로
            if self.get_val(row, 11) == 0:
                next_v = self.get_val(row + 1, 11)
                if next_v != 0 and check[row+1] == False:
                    check[row] = True
                    self.set_val(row, 11, next_v)
                    item = self.table.item(row, 11)
                    if item: item.setForeground(QColor("blue"))

        self.table.blockSignals(False)
        self.calculate_all_logic()
        print("2-Pass 환율 보정 완료 (앞 칸 우선순위 보장)")

    def reset_all_data(self):
        """모든 데이터를 초기화하고 Spread 열을 0.5초간 노란색으로 깜빡임"""
        self.table.blockSignals(True)
        
        # 1. 모든 값 0으로 초기화
        for row in range(12):
            for col in range(1, len(self.headers)):
                self.set_val(row, col, 0)
        
        # 2. 기본값 및 라벨 재설정 (스타일 포함)
        self.init_table_defaults()
        self.init_month_labels() 
        
        # 3. Spread 열(3번, 5번 컬럼)을 노란색으로 변경 (하이라이트 시작)
        for row in range(12):
            for col in [3, 5]: # MOPJ SPREAD, PX SPREAD
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("yellow"))
        
        self.table.blockSignals(False)

        # 4. 0.5초(500ms) 후 색상을 원래대로 돌리는 타이머 작동
        # 기존에 작성하신 init_month_labels가 배경색(강조색)을 다시 잡아주므로 이를 활용합니다.
        QTimer.singleShot(500, self.restore_table_style)

    def restore_table_style(self):
        """깜빡임이 끝난 후 테이블 스타일을 원래대로 복구"""
        self.table.blockSignals(True)
        
        # Spread 열의 노란색을 지우기 위해 배경색 초기화 (기본 흰색)
        for row in range(12):
            for col in [3, 5]:
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("white"))
        
        # 1, 5, 9월물 등에 적용된 배경색 강조를 다시 입힘
        self.init_month_labels()
        
        self.table.blockSignals(False)

    def export_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.headers)
                    for row in range(12):
                        row_data = [self.table.item(row, col).text() if self.table.item(row, col) else "" for col in range(len(self.headers))]
                        writer.writerow(row_data)
                QMessageBox.information(self, "성공", "파일이 생성되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "실패", str(e))