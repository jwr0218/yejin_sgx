import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QHeaderView, QComboBox, 
                             QPushButton, QLineEdit, QMessageBox, QGridLayout)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

# 기존 사용자 모듈 로드
try:
    from request.request_other import get_year_prices
    from request.request_sgx import get_year_sgx
    from screenshot import take_screenshot
except ImportError:
    # 테스트용 더미 함수
    def get_year_prices(code, count): return []
    def get_year_sgx(): return []
    def take_screenshot(a, b): pass

class Page3(QWidget):
    def __init__(self):
        super().__init__()
        self.months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        # 수식용 상수
        self.CONST_PX_PTA = 0.655 * 1.13 * 1.02
        self.CONST_ZCE_SGX = 1.13 * 1.02
        
        self.calculators = [] 
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        grid_layout = QGridLayout()

        # 4개 계산기 구성 (제목, 모드)
        calc_configs = [
            ("PX-PTA (1)", "PX-PTA"), ("PX-PTA (2)", "PX-PTA"),
            ("ZCE-SGX (1)", "ZCE-SGX"), ("ZCE-SGX (2)", "ZCE-SGX")
        ]

        for i, (title, mode) in enumerate(calc_configs):
            calc_widget = self.create_calculator_unit(title, mode)
            grid_layout.addWidget(calc_widget, i // 2, i % 2)

        main_layout.addLayout(grid_layout)

        # 하단 캡처 버튼
        self.btn_capture = QPushButton("화면 캡쳐 (save image)")
        self.btn_capture.setStyleSheet("background-color: #607D8B; color: white; padding: 12px; font-weight: bold; margin-top: 10px;")
        self.btn_capture.clicked.connect(lambda: take_screenshot(self, "Page3_Final_Result"))
        main_layout.addWidget(self.btn_capture)

        self.setLayout(main_layout)

    def create_calculator_unit(self, title_text, mode):
        container = QWidget()
        layout = QVBoxLayout()

        # 1. 제목 및 초기화 버튼
        title_row = QHBoxLayout()
        title = QLabel(f"● {title_text}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #333;")
        
        reset_btn = QPushButton("초기화")
        reset_btn.setFixedWidth(60)
        reset_btn.setStyleSheet("background-color: #E0E0E0; color: #333; font-size: 11px; border: 1px solid #BCBCBC;")
        
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(reset_btn)
        layout.addLayout(title_row)

        # 2. 상단 입력 테이블
        header_table = QTableWidget(1, 4)
        f_label = "pta future" if mode == "PX-PTA" else "px future"
        headers = ["month", "spread", f_label, "usd/chn"]
        
        header_table.setHorizontalHeaderLabels(headers)
        header_table.setFixedHeight(65)
        header_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_table.verticalHeader().setVisible(False)
        header_table.setStyleSheet("QHeaderView::section { background-color: #FDE9D9; font-weight: bold; border: 1px solid #D9D9D9; }")

        month_combo = QComboBox()
        month_combo.addItems(self.months)
        header_table.setCellWidget(0, 0, month_combo)

        spread_edit = QLineEdit()
        spread_edit.setPlaceholderText("입력")
        spread_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_table.setCellWidget(0, 1, spread_edit)

        future_cb = QComboBox()
        future_cb.setEditable(True)
        future_cb.setPlaceholderText("숫자-월")
        header_table.setCellWidget(0, 2, future_cb)

        usd_cb = QComboBox()
        usd_cb.setEditable(True)
        usd_cb.setPlaceholderText("숫자-월")
        header_table.setCellWidget(0, 3, usd_cb)

        # 3. 버튼 레이아웃
        btn_row = QHBoxLayout()
        fetch_btn = QPushButton("정보 가져오기")
        fetch_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; height: 28px;")
        calc_btn = QPushButton("계산 실행")
        calc_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; height: 28px;")
        btn_row.addWidget(fetch_btn)
        btn_row.addWidget(calc_btn)

        # 4. 결과 테이블
        # ZCE-SGX는 PX 입력을 받아 PTA를 시뮬레이션하고, PX-PTA는 PTA 입력을 받아 PX를 시뮬레이션함
        target_col_name = "PX" if mode == "PX-PTA" else "PTA"
        res_headers = ["month", target_col_name, "spread", f_label.split()[0], "usd/chn"]
        result_table = QTableWidget(9, 5)
        result_table.setHorizontalHeaderLabels(res_headers)
        result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        result_table.verticalHeader().setVisible(False)

        # Month 자동 동기화
        month_combo.currentTextChanged.connect(lambda val, rt=result_table: self.sync_month_column(val, rt))
        for r in range(9):
            result_table.setItem(r, 0, QTableWidgetItem(month_combo.currentText()))

        # 데이터 저장 및 시그널 연결
        calc_id = len(self.calculators)
        self.calculators.append({
            'mode': mode, 'header': header_table, 'result': result_table,
            'month_cb': month_combo, 'spread_le': spread_edit,
            'future_cb': future_cb, 'usd_cb': usd_cb
        })

        fetch_btn.clicked.connect(lambda _, cid=calc_id: self.on_fetch_clicked(cid))
        calc_btn.clicked.connect(lambda _, cid=calc_id: self.on_calculate_clicked(cid))
        reset_btn.clicked.connect(lambda _, cid=calc_id: self.on_reset_clicked(cid))

        layout.addWidget(header_table)
        layout.addLayout(btn_row)
        layout.addWidget(QLabel(f"▶ {title_text} 시뮬레이션 결과"))
        layout.addWidget(result_table)
        container.setLayout(layout)
        return container

    def on_reset_clicked(self, cid):
        """초기화: 입력값과 결과 테이블만 삭제"""
        calc = self.calculators[cid]
        calc['spread_le'].clear()
        calc['future_cb'].setEditText("")
        calc['usd_cb'].setEditText("")
        for r in range(calc['result'].rowCount()):
            for c in range(1, 5):
                calc['result'].setItem(r, c, QTableWidgetItem(""))

    def sync_month_column(self, value, table):
        for row in range(table.rowCount()):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 0, item)

    def parse_value(self, text):
        """'9494-JAN' 형식에서 숫자 추출"""
        if not text: return 0.0
        try: return float(text.split('-')[0].replace(',', ''))
        except: return 0.0

    def on_fetch_clicked(self, cid):
        calc = self.calculators[cid]
        mode = calc['mode']
        selected_month = calc['month_cb'].currentText().lower()
        month_idx = str(self.months.index(selected_month) + 1).zfill(2)
        
        try:
            # 1. 데이터 가져오기
            # PX-PTA 모드일 때는 PTA(nf_TA) 데이터, ZCE-SGX 모드일 때는 PX(nf_PX) 데이터를 가져옴
            if mode == "PX-PTA":
                future_data = get_year_prices("nf_TA", 8)
            else:
                future_data = get_year_prices("nf_PX", 8) # 알려주신 PX 코드 반영
            
            usd_data = get_year_sgx()

            # 2. 콤보박스 아이템 생성
            calc['future_cb'].clear()
            calc['usd_cb'].clear()
            
            f_target_text = ""
            u_target_text = ""

            # Future 칸 처리
            for item in future_data:
                p = item.get('price', '0')
                m_n = item.get('month', '').split('/')[-1]
                m_str = self.months[int(m_n)-1].upper() if m_n.isdigit() else "???"
                display_txt = f"{p}-{m_str}"
                calc['future_cb'].addItem(display_txt)
                if m_n == month_idx: f_target_text = display_txt

            # USD/CHN 칸 처리
            for item in usd_data:
                p = item.get('price', '0')
                m_n = item.get('month', '').split('/')[-1]
                m_str = self.months[int(m_n)-1].upper() if m_n.isdigit() else "???"
                display_txt = f"{p}-{m_str}"
                calc['usd_cb'].addItem(display_txt)
                if m_n == month_idx: u_target_text = display_txt

            # 3. 값 자동 입력
            if f_target_text: calc['future_cb'].setEditText(f_target_text)
            if u_target_text: calc['usd_cb'].setEditText(u_target_text)

            # 4. Blink 효과 적용
            flash_style = "background-color: #FFF176; border: 1px solid #FBC02D; font-weight: bold;"
            calc['future_cb'].setStyleSheet(flash_style)
            calc['usd_cb'].setStyleSheet(flash_style)
            
            # 0.6초 후 스타일 초기화
            QTimer.singleShot(600, lambda: self.reset_flash_style(calc))

        except Exception as e:
            print(f"Fetch Error: {e}")

    def reset_flash_style(self, calc):
        calc['future_cb'].setStyleSheet("")
        calc['usd_cb'].setStyleSheet("")

    def on_calculate_clicked(self, cid):
        calc = self.calculators[cid]
        mode = calc['mode']
        const_val = self.CONST_PX_PTA if mode == "PX-PTA" else self.CONST_ZCE_SGX
        
        try:
            m = calc['month_cb'].currentText()
            s = float(calc['spread_le'].text())
            f = self.parse_value(calc['future_cb'].currentText())
            u = self.parse_value(calc['usd_cb'].currentText())

            if u == 0: return

            # 역산 수식
            if mode == "PX-PTA":
                # f=PTA Future, PX를 역산: PX = (PTA - Spread) / (Const * USD)
                center_val = (f - s) / (const_val * u)
            else:
                # f=PX Future, PTA를 역산: PTA = (PX * Const * USD) + Spread
                center_val = (f * const_val * u) + s

            offsets = [-2.0, -1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0]

            for row, offset in enumerate(offsets):
                curr_val = center_val + offset
                # Spread 재계산
                if mode == "PX-PTA":
                    calc_s = f - (curr_val * const_val * u)
                else:
                    calc_s = curr_val - (f * const_val * u)

                calc['result'].setItem(row, 0, QTableWidgetItem(m))
                calc['result'].setItem(row, 1, QTableWidgetItem(f"{curr_val:.1f}"))
                calc['result'].setItem(row, 2, QTableWidgetItem(f"{calc_s:.2f}"))
                calc['result'].setItem(row, 3, QTableWidgetItem(f"{f:,.0f}"))
                calc['result'].setItem(row, 4, QTableWidgetItem(f"{u:.4f}"))

                for col in range(5):
                    it = calc['result'].item(row, col)
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if offset == 0:
                        it.setBackground(QColor("#E8F5E9"))
                        font = it.font()
                        font.setBold(True)
                        it.setFont(font)
        except:
            QMessageBox.critical(self, "오류", "입력값을 확인하세요.")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = Page3()
    window.show()
    sys.exit(app.exec())