import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from dateutil.relativedelta import relativedelta

import config
from request.request_other import get_year_prices, get_year_prev_close
from screenshot import take_screenshot

class Page2(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.pta_data = {}
        self.px_data = {}

        self.table = QTableWidget(0, 5)
        headers = ["Item", "yday", "tday", "+/-", "usd+/-"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setStyleSheet(config.HEADER_STYLE)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table, 3)

        self.legend = QLabel("회색 행 = 거래 종료(만기 등) 월물. 표시된 값은 마지막으로 거래된 날의 최종 가격이며, 마우스를 올리면 그 날짜를 확인할 수 있습니다.")
        self.legend.setStyleSheet("color: #757575; font-size: 11px;")
        self.legend.setWordWrap(True)
        layout.addWidget(self.legend)

        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("데이터 불러오기")
        self.btn_load.clicked.connect(self.load_all_market_data)

        self.btn_capture = QPushButton("화면 캡처 (Save Image)")
        self.btn_capture.clicked.connect(lambda: take_screenshot(self, "Page2"))

        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_capture)
        layout.addLayout(btn_layout)

        # 월물 스프레드 비교 패널 (두 월물을 선택해 스프레드 비교)
        self.compare_group = QGroupBox("월물 스프레드 비교")
        compare_layout = QVBoxLayout()

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("상품"))
        self.compare_product_cb = QComboBox()
        self.compare_product_cb.addItems(["PTA", "PX"])
        self.compare_product_cb.currentTextChanged.connect(self.refresh_compare_months)
        control_layout.addWidget(self.compare_product_cb)

        control_layout.addWidget(QLabel("월물1"))
        self.compare_month1_cb = QComboBox()
        control_layout.addWidget(self.compare_month1_cb)

        control_layout.addWidget(QLabel("월물2"))
        self.compare_month2_cb = QComboBox()
        control_layout.addWidget(self.compare_month2_cb)

        self.btn_compare = QPushButton("비교")
        self.btn_compare.clicked.connect(self.on_compare_clicked)
        control_layout.addWidget(self.btn_compare)

        self.btn_compare_reset = QPushButton("초기화")
        self.btn_compare_reset.clicked.connect(lambda: self.compare_table.setRowCount(0))
        control_layout.addWidget(self.btn_compare_reset)

        compare_layout.addLayout(control_layout)

        self.compare_table = QTableWidget(0, 5)
        self.compare_table.setHorizontalHeaderLabels(headers)
        self.compare_table.setStyleSheet(config.HEADER_STYLE)
        self.compare_table.verticalHeader().setVisible(False)
        self.compare_table.verticalHeader().setDefaultSectionSize(24)
        self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.compare_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 헤더 + 1개 행 높이만큼만 고정 (그 이상 스크롤/공백 없이 딱 한 행만 표시)
        self.compare_table.setFixedHeight(self.compare_table.horizontalHeader().height() + 24 + 4)
        compare_layout.addWidget(self.compare_table)

        self.compare_group.setLayout(compare_layout)
        layout.addWidget(self.compare_group, 1)

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
        
        # 1(다음달)부터 12까지 탐색 (당월 제외, page1과 동일 기준)
        for i in range(12):
            check_date = now + relativedelta(months=i+1)
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
        # 오늘 거래가(tday)는 기존 실시간 시세 API, 전일 종가(yday)는 일별 K차트에서
        # 날짜 검증된 값으로 각각 받아와 합친다 (전일 결제가 혼동 방지).
        pta_t_raw = get_year_prices("nf_TA", 8)
        px_t_raw = get_year_prices("nf_PX", 8)
        pta_yday = get_year_prev_close("TA")
        px_yday = get_year_prev_close("PX")

        def to_data_dict(t_raw, yday_dict):
            merged = {}
            for item in t_raw:
                if item['month'] == "N/A":
                    continue
                parts = item['month'].split('/')
                yy, mm = int(parts[0]) % 100, int(parts[1])

                yday = yday_dict.get((yy, mm))
                if yday is None:
                    continue

                # 오늘자 거래가가 아직 없으면(N/A) 0으로 표시하되 행은 유지
                tday = float(item['price']) if item['price'] != "N/A" else 0
                merged[(yy, mm)] = {'tday': tday, 'yday': yday,
                                    'date': item.get('date'),
                                    'stale': bool(item.get('stale'))}
            return merged

        pta_data = to_data_dict(pta_t_raw, pta_yday)
        px_data = to_data_dict(px_t_raw, px_yday)

        self.pta_data = pta_data
        self.px_data = px_data

        self.table.setRowCount(0)

        # 타겟 월물 리스트 가져오기
        target_list = self.get_target_months()

        # 제품별 행 추가
        self.add_product_rows("PTA", pta_data, target_list)
        self.add_product_rows("PX", px_data, target_list)

        # 비교 패널 월물 콤보박스 갱신
        self.refresh_compare_months()
        
        # self.table.resizeColumnsToContents()

    def add_product_rows(self, name, data_dict, target_list):
        """동적 타겟 리스트를 기반으로 행 추가 (형식: 26-JAN)"""
        active_info = {}

        # 1. 월물별 데이터 출력
        for t in target_list:
            yy = t['year'] % 100  # 2026 -> 26
            mm = t['month']

            if (yy, mm) in data_dict:
                info = data_dict[(yy, mm)]
                active_info[mm] = {**info, 'yy': yy}

                # 라벨 형식을 YY-MONTH (예: PTA 26-JAN) 로 변경
                label = f"{name} {yy}-{self._month_name(mm)}"
                self._insert_row(self.table, label, info['yday'], info['tday'],
                                 stale=info.get('stale'), note=self._stale_note(info))

        # 2. 스프레드 항목 추가 (데이터가 존재하는 경우에만)
        # 라벨은 숫자(예: 1/3)로 표시한다. 1/9는 9/1(항상 연도가 바뀌는 전용 스프레드)과
        # 내용이 겹칠 수 있어 별도로 두지 않고 9/1 하나로 통일한다.
        # 1월은 시점에 따라 다음 해로 넘어가 있을 수 있어 m1/m2 숫자 순서만으로는
        # 근월물이 항상 앞에 온다고 보장할 수 없으므로, 실제 연도까지 비교해 정렬한다.
        spread_targets = [
            {"m1": 1, "m2": 3},
            {"m1": 3, "m2": 5},
            {"m1": 1, "m2": 5},
            {"m1": 5, "m2": 9},
        ]

        # 각 스프레드를 근월 다리의 (연도,월) 기준 정렬 키와 함께 모아뒀다가,
        # 전부 계산한 뒤 근월이 빠른 순서대로 한꺼번에 삽입한다.
        spread_rows = []

        for s in spread_targets:
            m1, m2 = s["m1"], s["m2"]
            if m1 in active_info and m2 in active_info:
                v1, v2 = active_info[m1], active_info[m2]

                # 근월물이 항상 앞에 오도록 (연도, 월) 기준으로 비교해 정렬
                if (v1['yy'], m1) <= (v2['yy'], m2):
                    near_m, near_v, far_m, far_v = m1, v1, m2, v2
                else:
                    near_m, near_v, far_m, far_v = m2, v2, m1, v1

                s_yday = near_v['yday'] - far_v['yday']
                s_tday = near_v['tday'] - far_v['tday']

                label = f"{near_m}/{far_m}"
                # 스프레드 이름 (예: PTA 1/3) - 한 다리라도 거래 정지면 스프레드도 신뢰 불가
                spread_rows.append({
                    'sort_key': (near_v['yy'], near_m),
                    'label': f"{name} {label}", 's_yday': s_yday, 's_tday': s_tday,
                    'stale': near_v.get('stale') or far_v.get('stale'),
                    'note': self._stale_note(near_v, far_v),
                })

        # 9/1 스프레드: "다음 해로 넘어가는 9월→1월" 스프레드는 항상 연도가 바뀌도록 고정
        # (active_info의 1월은 현재 시점에 따라 9월보다 앞선 해일 수도 있어 그대로 쓰면 안 됨)
        if 9 in active_info:
            sep_info = active_info[9]
            jan_yy = (sep_info['yy'] + 1) % 100
            jan_info = data_dict.get((jan_yy, 1))
            if jan_info is not None:
                s_yday = sep_info['yday'] - jan_info['yday']
                s_tday = sep_info['tday'] - jan_info['tday']
                spread_rows.append({
                    'sort_key': (sep_info['yy'], 9),
                    'label': f"{name} 9/1", 's_yday': s_yday, 's_tday': s_tday,
                    'stale': sep_info.get('stale') or jan_info.get('stale'),
                    'note': self._stale_note(sep_info, jan_info),
                })

        # 3. 근월 변동폭: m+1/m+2, m+2/m+3, m+1/m+3 (고정 스프레드와 한데 모아서 같이 정렬)
        spread_rows.extend(self._build_near_spread_rows(name, data_dict))

        # 근월(연도,월)이 빠른 것부터 위에 오도록 전체를 한 번에 정렬해서 삽입
        for r in sorted(spread_rows, key=lambda r: r['sort_key']):
            self._insert_row(self.table, r['label'], r['s_yday'], r['s_tday'],
                             stale=r['stale'], note=r['note'])

    def _build_near_spread_rows(self, name, data_dict):
        """
        당월(m) 기준 익월물 3개(m+1, m+2, m+3)로 아래 스프레드를 계산해 행 목록으로 반환한다.
            m+1/m+2, m+2/m+3, m+1/m+3

        relativedelta가 월 덧셈 시 연도를 함께 넘겨주므로 12월을 넘어가면
        자동으로 다음 해 1월이 된다. (예: 11월 -> m+2는 다음 해 1월)
        """
        now = datetime.datetime.now()
        months = {}
        for i in (1, 2, 3):
            d = now + relativedelta(months=i)
            yy, mm = d.year % 100, d.month
            months[i] = {"yy": yy, "mm": mm, "info": data_dict.get((yy, mm))}

        rows = []
        pairs = [(1, 2), (2, 3), (1, 3)]  # m+1/m+2, m+2/m+3, m+1/m+3
        for i1, i2 in pairs:
            a, b = months[i1], months[i2]
            if a["info"] is None or b["info"] is None:
                continue
            s_yday = a["info"]["yday"] - b["info"]["yday"]
            s_tday = a["info"]["tday"] - b["info"]["tday"]
            label = f"{name} {a['mm']}/{b['mm']}"
            rows.append({
                'sort_key': (a['yy'], a['mm']),
                'label': label, 's_yday': s_yday, 's_tday': s_tday,
                'stale': a["info"].get('stale') or b["info"].get('stale'),
                'note': self._stale_note(a["info"], b["info"]),
            })
        return rows

    def _insert_row(self, table, label, yday, tday, stale=False, note=""):
        """
        stale=True는 만기 등으로 거래가 멈춘 월물(마지막 체결가가 그대로 남아 있는 상태).
        값은 그대로 보여주되 회색 배경으로만 실시간 시세와 구분한다 (라벨 텍스트는 그대로).
        """
        row = table.rowCount()
        table.insertRow(row)

        item_label = QTableWidgetItem(label)
        item_label.setBackground(QColor("#E0E0E0") if stale else QColor("#D9EAD3"))
        table.setItem(row, 0, item_label)

        # yday, tday
        table.setItem(row, 1, QTableWidgetItem(f"{yday:,.2f}"))
        table.setItem(row, 2, QTableWidgetItem(f"{tday:,.2f}"))

        # +/-
        diff = tday - yday
        diff_item = QTableWidgetItem(f"{diff:+.2f}")
        if diff > 0: diff_item.setForeground(QColor("red"))
        elif diff < 0: diff_item.setForeground(QColor("blue"))
        table.setItem(row, 3, diff_item)

        # usd+/-
        usd_diff = diff / 7.2
        usd_item = QTableWidgetItem(f"{usd_diff:+.2f}")
        if usd_diff > 0: usd_item.setForeground(QColor("red"))
        elif usd_diff < 0: usd_item.setForeground(QColor("blue"))
        table.setItem(row, 4, usd_item)

        for i in range(5):
            it = table.item(row, i)
            if it:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if stale:
                    # +/- 의 빨강/파랑보다 뒤에 적용해 회색이 최종적으로 남도록 한다.
                    it.setForeground(QColor("#9E9E9E"))
                    it.setToolTip(note)

    def _stale_dates(self, *infos):
        """거래가 멈춘 월물들의 마지막 시세 일자 목록 (오래된 순)."""
        return sorted({i['date'] for i in infos if i.get('stale') and i.get('date')})

    def _stale_note(self, *infos):
        """거래가 멈춘 월물의 마지막 시세 일자를 툴팁 문구로 만든다."""
        dates = self._stale_dates(*infos)
        if not dates:
            return ""
        return "거래 종료(만기 등)로 실시간 시세가 아님\n마지막 시세 일자: " + ", ".join(dates)

    def _month_name(self, m):
        return ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"][m]

    def refresh_compare_months(self):
        """비교 패널의 월물1/월물2 콤보박스를 현재 선택된 상품의 로드된 월물로 갱신"""
        product = self.compare_product_cb.currentText()
        data_dict = self.pta_data if product == "PTA" else self.px_data

        for cb in (self.compare_month1_cb, self.compare_month2_cb):
            cb.blockSignals(True)
            cb.clear()
            for yy, mm in sorted(data_dict.keys()):
                cb.addItem(f"{yy:02d}-{self._month_name(mm)}", (yy, mm))
            cb.blockSignals(False)

    def on_compare_clicked(self):
        """선택한 두 월물의 스프레드(yday/tday/변동폭)를 비교 테이블에 추가"""
        product = self.compare_product_cb.currentText()
        data_dict = self.pta_data if product == "PTA" else self.px_data

        if not data_dict:
            QMessageBox.warning(self, "알림", "먼저 데이터를 불러와주세요.")
            return

        key1 = self.compare_month1_cb.currentData()
        key2 = self.compare_month2_cb.currentData()
        if key1 is None or key2 is None or key1 == key2:
            QMessageBox.warning(self, "알림", "서로 다른 두 월물을 선택해주세요.")
            return

        v1, v2 = data_dict.get(key1), data_dict.get(key2)
        if not v1 or not v2:
            QMessageBox.warning(self, "알림", "선택한 월물의 데이터가 없습니다.")
            return

        # 근월물이 항상 앞에 오도록 (연도, 월) 기준으로 정렬
        if key1 <= key2:
            near_v, near_text, far_v, far_text = v1, self.compare_month1_cb.currentText(), v2, self.compare_month2_cb.currentText()
        else:
            near_v, near_text, far_v, far_text = v2, self.compare_month2_cb.currentText(), v1, self.compare_month1_cb.currentText()

        label = f"{product} {near_text}/{far_text}"
        s_yday = near_v['yday'] - far_v['yday']
        s_tday = near_v['tday'] - far_v['tday']
        self.compare_table.setRowCount(0)
        self._insert_row(self.compare_table, label, s_yday, s_tday,
                         stale=v1.get('stale') or v2.get('stale'),
                         note=self._stale_note(v1, v2))