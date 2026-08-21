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

        # 2. 스프레드 항목 추가
        # 라벨은 숫자(예: 1/3)로 표시한다. 1/9는 9/1(항상 연도가 바뀌는 전용 스프레드)과
        # 내용이 겹칠 수 있어 별도로 두지 않고 9/1 하나로 통일한다.
        #
        # 다리를 (연도, 월) 키로 확정한 뒤 시세를 붙인다. 월 숫자만으로는 근월물이
        # 항상 앞에 온다고 보장할 수 없기 때문이다(1월은 시점에 따라 다음 해).
        # 시세가 없어 계산할 수 없는 조합도 행은 남기고 N/A로 표시한다 - 항상
        # 지켜보는 스프레드가 조용히 사라지면 빠진 줄 모르기 때문이다.
        spread_rows = []
        seen = set()

        def add_spread(near_key, far_key):
            """near_key/far_key = (yy, mm). 같은 조합이 두 번 들어오면 무시한다."""
            if near_key == far_key or (near_key, far_key) in seen:
                return
            seen.add((near_key, far_key))

            near_v, far_v = data_dict.get(near_key), data_dict.get(far_key)
            row = {
                'sort_key': near_key,
                'label': f"{name} {near_key[1]}/{far_key[1]}",
                's_yday': None, 's_tday': None, 'stale': False, 'note': '',
            }
            if near_v is None or far_v is None:
                missing = [k for k, v in ((near_key, near_v), (far_key, far_v)) if v is None]
                row['note'] = ("시세가 없어 계산할 수 없음\n해당 월물: "
                               + ", ".join(f"{yy:02d}-{self._month_name(mm)}" for yy, mm in missing))
            else:
                row['s_yday'] = near_v['yday'] - far_v['yday']
                row['s_tday'] = near_v['tday'] - far_v['tday']
                # 한 다리라도 거래 정지면 스프레드도 신뢰 불가
                row['stale'] = near_v.get('stale') or far_v.get('stale')
                row['note'] = self._stale_note(near_v, far_v)
            spread_rows.append(row)

        # 타겟 월물의 연도표. 시세 유무와 무관하게 잡아둬야 N/A 행도 만들 수 있다.
        target_yy = {t['month']: t['year'] % 100 for t in target_list}

        def key_of(mm):
            return (target_yy[mm], mm) if mm in target_yy else None

        # 주력월 스프레드 (근월이 앞에 오도록 연도까지 비교)
        for m1, m2 in ((1, 3), (3, 5), (1, 5), (5, 9)):
            k1, k2 = key_of(m1), key_of(m2)
            if k1 and k2:
                add_spread(*sorted((k1, k2)))

        # 9/1: 9월 -> 다음 해 1월. 항상 해를 넘기도록 고정한다.
        # (target_yy의 1월은 시점에 따라 9월보다 앞선 해일 수 있어 그대로 쓰면 안 됨)
        sep_key = key_of(9)
        if sep_key:
            add_spread(sep_key, ((sep_key[0] + 1) % 100, 1))

        # 5/9: 같은 해 5월 -> 9월. 위 주력월 스프레드의 5/9는 시점에 따라
        # '올해 9월 - 내년 5월'로 잡히므로, 해를 넘기지 않는 5/9를 따로 둔다.
        may_key = key_of(5)
        if may_key:
            add_spread(may_key, (may_key[0], 9))

        # 3. 근월 변동폭: m+1/m+2, m+2/m+3, m+1/m+3 (고정 스프레드와 한데 모아서 같이 정렬)
        for near_key, far_key in self._near_spread_pairs():
            add_spread(near_key, far_key)

        # 근월(연도,월)이 빠른 것부터 위에 오도록 전체를 한 번에 정렬해서 삽입
        for r in sorted(spread_rows, key=lambda r: r['sort_key']):
            self._insert_row(self.table, r['label'], r['s_yday'], r['s_tday'],
                             stale=r['stale'], note=r['note'])

    def _near_spread_pairs(self):
        """
        당월(m) 기준 익월물 3개(m+1, m+2, m+3)로 만드는 스프레드 다리 목록.
            m+1/m+2, m+2/m+3, m+1/m+3

        relativedelta가 월 덧셈 시 연도를 함께 넘겨주므로 12월을 넘어가면
        자동으로 다음 해 1월이 된다. (예: 11월 -> m+2는 다음 해 1월)
        m+1 < m+2 < m+3 이므로 앞쪽이 항상 근월이다.
        """
        now = datetime.datetime.now()
        months = {}
        for i in (1, 2, 3):
            d = now + relativedelta(months=i)
            months[i] = (d.year % 100, d.month)
        return [(months[a], months[b]) for a, b in ((1, 2), (2, 3), (1, 3))]

    def _insert_row(self, table, label, yday, tday, stale=False, note=""):
        """
        stale=True는 만기 등으로 거래가 멈춘 월물(마지막 체결가가 그대로 남아 있는 상태).
        값은 그대로 보여주되 회색 배경으로만 실시간 시세와 구분한다 (라벨 텍스트는 그대로).

        yday/tday가 None이면 시세가 없어 계산할 수 없는 경우로, 행은 남기고
        N/A로 표시한다. 사유는 note(툴팁)로 알린다.
        """
        row = table.rowCount()
        table.insertRow(row)
        missing = yday is None or tday is None

        item_label = QTableWidgetItem(label)
        item_label.setBackground(QColor("#E0E0E0") if stale else QColor("#D9EAD3"))
        table.setItem(row, 0, item_label)

        # yday, tday
        table.setItem(row, 1, QTableWidgetItem("N/A" if yday is None else f"{yday:,.2f}"))
        table.setItem(row, 2, QTableWidgetItem("N/A" if tday is None else f"{tday:,.2f}"))

        if missing:
            # 한쪽이라도 없으면 변동폭 자체가 성립하지 않는다.
            table.setItem(row, 3, QTableWidgetItem("N/A"))
            table.setItem(row, 4, QTableWidgetItem("N/A"))
        else:
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
                if stale or missing:
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