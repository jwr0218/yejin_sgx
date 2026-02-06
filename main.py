import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QStackedWidget)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt

from datetime import datetime
from dateutil.relativedelta import relativedelta

from page.page1 import Page1
from page.page2 import Page2
from page.page3 import Page3
from request.request_other import get_year_prices
# from request_sgx import get_year_sgx , turn_off_driver
# 공통 스타일: 엑셀 느낌의 헤더 스타일

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Market Analysis Tool")
        self.resize(1100, 600)

        # 중앙 위젯과 메인 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 상단 페이지 전환 내비게이션 버튼
        nav_layout = QHBoxLayout()
        self.btn_page1 = QPushButton("Page 1")
        self.btn_page2 = QPushButton("Page 2")
        self.btn_page3 = QPushButton("Page 3")
        nav_layout.addWidget(self.btn_page1)
        nav_layout.addWidget(self.btn_page2)
        nav_layout.addWidget(self.btn_page3)
        main_layout.addLayout(nav_layout)

        # 페이지를 담을 스택 위젯 생성
        self.stack = QStackedWidget()
        self.page1 = Page1()
        self.page2 = Page2()
        self.page3 = Page3()
        self.stack.addWidget(self.page1)
        self.stack.addWidget(self.page2)
        self.stack.addWidget(self.page3)
        main_layout.addWidget(self.stack)

        # 버튼 클릭 이벤트 연결
        self.btn_page1.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_page2.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_page3.clicked.connect(lambda: self.stack.setCurrentIndex(2))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    
    sys.exit(app.exec())
    turn_off_driver()