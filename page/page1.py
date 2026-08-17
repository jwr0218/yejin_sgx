import datetime
import csv
import os
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QTimer, QEvent
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
        
        self.table = QTableWidget(11, len(self.headers))   # 당월 제외, 다음 달부터 11개월
        self.table.setHorizontalHeaderLabels(self.headers)
        
        # UI 초기화 및 스타일 적용
        self.init_table_defaults()
        self.init_month_labels() # 강조 로직 포함
        
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.installEventFilter(self)
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

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.legend = QLabel("회색 숫자 = 거래 종료(만기 등)된 월물. 표시된 값은 마지막으로 거래된 날의 최종 가격이며, 마우스를 올리면 그 날짜를 확인할 수 있습니다. 예) Brent는 인도월 2개월 전에 만기되어 최근월물이 이미 종료된 상태일 수 있습니다.")
        self.legend.setStyleSheet("color: #757575; font-size: 11px;")
        self.legend.setWordWrap(True)
        layout.addWidget(self.legend)

        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def eventFilter(self, source, event):
        if source is self.table and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                current = self.table.currentIndex()
                next_row = current.row() + 1
                if next_row < self.table.rowCount():
                    self.table.setCurrentCell(next_row, current.column())
                return True
        return super().eventFilter(source, event)

    def init_table_defaults(self):
        for row in range(self.table.rowCount()):
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

        # 각 행이 어느 월물인지를 "YY/MM" 키로 보관해 둔다.
        # 라벨과 데이터 매핑이 같은 계산에서 나오도록 하기 위한 것으로,
        # 이 목록이 시세를 붙일 때의 유일한 기준이 된다. (load_all_market_data 참조)
        self.row_months = []

        for i in range(self.table.rowCount()):
            # 당월 제외, 다음 달부터 표시한다.
            target_date = now + relativedelta(months=i + 1)
            month_int = target_date.month
            self.row_months.append(target_date.strftime("%y/%m"))
            
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
        # USD/CNH(11)는 소수점 4자리 적용
        elif col == 11:
            precision = 4
            
        item = self.table.item(row, col)
        if not item:
            item = QTableWidgetItem()
            self.table.setItem(row, col, item)
        
        item.setText(f"{val:,.{precision}f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if not is_editable:
            item.setBackground(QColor("#F0F4F8"))
        self.table.blockSignals(False)

    def _apply_quote_state(self, row, col, info):
        """
        거래 정지(만기 등) 월물의 셀을 회색 글자로만 구분 표시한다(날짜는 툴팁으로).
        재로딩 시 살아난 월물의 표시가 남지 않도록 정상 상태도 명시적으로 되돌린다.
        """
        item = self.table.item(row, col)
        if not item:
            return
        if info.get('stale'):
            date = info.get('date') or ""
            item.setForeground(QColor("#9E9E9E"))
            item.setToolTip(f"거래 종료(만기 등)로 실시간 시세가 아님\n마지막 시세 일자: {date}")
        else:
            item.setForeground(QColor("black"))
            item.setToolTip("")

    def on_item_changed(self, item):
        col = item.column()
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # 추가
        if col in [1, 2, 3, 4, 5, 7, 8, 11]:
            self.calculate_all_logic()

    def calculate_all_logic(self):
        """계단식 로직 및 수식 계산"""
        for row in range(self.table.rowCount()):
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

        for row in range(self.table.rowCount()):
            self.set_val(row, 12, self.get_val(row, 6) - self.get_val(row+1, 6))

    def get_val(self, row, col):
        if row < 0 or row >= self.table.rowCount(): return 0.0
        item = self.table.item(row, col)
        if not item or not item.text() or item.text() == "N/A": return 0.0
        try:
            return float(item.text().replace(',', ''))
        except ValueError:
            return 0.0

    def load_all_market_data(self):
        """API 로드 및 2-Pass 보정 (당월 제외, 다음 달부터 로드)"""
        self.table.blockSignals(True)
        
        # 1. API 데이터 기본 로드
        pta_data = get_year_prices("nf_TA", 8)
        px_future_data = get_year_prices("nf_PX", 8)
        # hf_(외방 선물)는 nf_(내수 선물)와 필드 배열이 달라 현재가가 0번이다.
        # 8번은 '전일 결제가'라 장중에 값이 갱신되지 않는다.
        brent_oil = get_year_prices("hf_OIL", 0)
        sgx_value = get_year_sgx()

        # 시세는 배열 순서가 아니라 '당월 기준 +N개월' 월물 키로 찾아 붙인다.
        # 응답이 어느 월물부터 시작하는지는 소스마다 다르고, 특히 SGX는 당월물
        # 만기 여부에 따라 첫 항목이 매달 바뀌므로 인덱스로 맞추면 어긋난다.
        # self.row_months는 행 라벨을 만든 계산 그대로이므로 라벨과 항상 일치한다.
        def by_month(rows):
            return {r['month']: r for r in rows if r.get('month') not in (None, 'N/A')}

        sources = {1: by_month(brent_oil), 7: by_month(px_future_data),
                   8: by_month(pta_data), 11: by_month(sgx_value)}

        for row, key in enumerate(self.row_months):
            for col in (1, 7, 8):
                info = sources[col].get(key)
                if info and info['price'] != 'N/A':
                    self.set_val(row, col, float(info['price']))
                    # 만기 등으로 거래가 멈춘 월물은 마지막 체결가가 그대로 내려오므로
                    # 실시간 시세와 눈으로 구분되도록 표시해 둔다.
                    self._apply_quote_state(row, col, info)

            sgx_info = sources[11].get(key)
            if sgx_info and sgx_info['price'] != 'N/A':
                self.set_val(row, 11, float(sgx_info['price']))
                item = self.table.item(row, 11)
                if item: item.setForeground(QColor("black"))
            else:
                self.set_val(row, 11, 0)

        # 2. [Pass 1] 순방향 보정: 앞 칸(위)의 값을 아래로 전파 (앞 칸 우선 논리)
        rows = self.table.rowCount()
        check = [False] * (rows + 1)   # check[row+1] 접근이 있어 +1 여유

        for row in range(1, rows): # 1번 행부터 시작
            if self.get_val(row, 11) == 0 :
                prev_v = self.get_val(row - 1, 11)
                if prev_v != 0 and check[row-1] == False:
                    check[row] = True
                    self.set_val(row, 11, prev_v)
                    item = self.table.item(row, 11)
                    if item: item.setForeground(QColor("blue"))

        # 3. [Pass 2] 역방향 보정: 여전히 0인 칸은 뒷 칸(아래)의 값을 위로 전파
        for row in range(rows - 2, -1, -1): # 마지막 직전 행부터 0번 행까지 거꾸로
            if self.get_val(row, 11) == 0:
                next_v = self.get_val(row + 1, 11)
                if next_v != 0 and check[row+1] == False:
                    check[row] = True
                    self.set_val(row, 11, next_v)
                    item = self.table.item(row, 11)
                    if item: item.setForeground(QColor("blue"))

        self.table.blockSignals(False)
        self.calculate_all_logic()
        print("2-Pass 환율 보정 및 당월 제외 데이터 로드 완료")

    # def load_all_market_data(self):
        # """API 로드 및 2-Pass 보정 (앞 칸 우선 채우기 -> 남은 빈칸 뒷 칸 채우기)"""
        # self.table.blockSignals(True)
        
        # # 1. API 데이터 기본 로드 (기존 소스 동일)
        # pta_data = get_year_prices("nf_TA", 8)
        # px_future_data = get_year_prices("nf_PX", 8)
        # brent_oil = get_year_prices("hf_OIL", 8)
        # sgx_value = get_year_sgx()

        # for row in range(12):
        #     if row < len(brent_oil) and brent_oil[row]['price'] != 'N/A':
        #         self.set_val(row, 1, float(brent_oil[row]['price']))
        #     if row < len(px_future_data) and px_future_data[row]['price'] != 'N/A':
        #         self.set_val(row, 7, float(px_future_data[row]['price']))
        #     if row < len(pta_data) and pta_data[row]['price'] != 'N/A':
        #         self.set_val(row, 8, float(pta_data[row]['price']))
            
        #     if row < len(sgx_value) and sgx_value[row]['price'] != 'N/A':
        #         self.set_val(row, 11, float(sgx_value[row]['price']))
        #         item = self.table.item(row, 11)
        #         if item: item.setForeground(QColor("black"))
        #     else:
        #         self.set_val(row, 11, 0)

        # # 2. [Pass 1] 순방향 보정: 앞 칸(위)의 값을 아래로 전파 (앞 칸 우선 논리)
        # check = [False for i in range(1,13)]

        # for row in range(1, 12): # 1번 행부터 시작
        #     if self.get_val(row, 11) == 0 :
        #         prev_v = self.get_val(row - 1, 11)
        #         if prev_v != 0 and check[row-1] == False:
        #             check[row] = True
        #             self.set_val(row, 11, prev_v)
        #             item = self.table.item(row, 11)
        #             if item: item.setForeground(QColor("blue"))

        # # 3. [Pass 2] 역방향 보정: 여전히 0인 칸은 뒷 칸(아래)의 값을 위로 전파
        # for row in range(10, -1, -1): # 10번 행부터 0번 행까지 거꾸로
        #     if self.get_val(row, 11) == 0:
        #         next_v = self.get_val(row + 1, 11)
        #         if next_v != 0 and check[row+1] == False:
        #             check[row] = True
        #             self.set_val(row, 11, next_v)
        #             item = self.table.item(row, 11)
        #             if item: item.setForeground(QColor("blue"))

        # self.table.blockSignals(False)
        # self.calculate_all_logic()
        # print("2-Pass 환율 보정 완료 (앞 칸 우선순위 보장)")

    def reset_all_data(self):
        """모든 데이터를 초기화하고 Spread 열을 0.5초간 노란색으로 깜빡임"""
        self.table.blockSignals(True)
        
        # 1. 모든 값 0으로 초기화
        for row in range(self.table.rowCount()):
            for col in range(1, len(self.headers)):
                self.set_val(row, col, 0)
        
        # 2. 기본값 및 라벨 재설정 (스타일 포함)
        self.init_table_defaults()
        self.init_month_labels() 
        
        # 3. Spread 열(3번, 5번 컬럼)을 노란색으로 변경 (하이라이트 시작)
        for row in range(self.table.rowCount()):
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
        for row in range(self.table.rowCount()):
            for col in [3, 5]:
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("white"))
        
        # 1, 5, 9월물 등에 적용된 배경색 강조를 다시 입힘
        self.init_month_labels()
        
        self.table.blockSignals(False)

    def export_to_csv(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.join(base_dir, "..", "excel_exports")
        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.csv"
        path = os.path.join(save_dir, filename)

        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
                for row in range(self.table.rowCount()):
                    row_data = [self.table.item(row, col).text() if self.table.item(row, col) else "" for col in range(len(self.headers))]
                    writer.writerow(row_data)
            os.startfile(os.path.abspath(path))
            os.startfile(os.path.abspath(save_dir))
        except Exception as e:
            QMessageBox.critical(self, "실패", str(e))