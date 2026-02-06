import os
import sys
import datetime
from PyQt6.QtWidgets import QMessageBox

def take_screenshot(widget, page_name):
    # 1. 실행 파일의 실제 위치 기반 경로 설정
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 경우 (.exe/.app 실행 위치)
        base_dir = os.path.dirname(sys.executable)
    else:
        # 일반 파이썬 실행 환경
        base_dir = os.path.abspath(".")

    save_dir = os.path.join(base_dir, "screenshot")
    
    # 2. 폴더 생성
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 3. 파일명 및 절대 경로 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{page_name}_{timestamp}.png"
    file_path = os.path.join(save_dir, file_name)
    
    # 4. 캡처 및 저장
    pixmap = widget.grab()
    success = pixmap.save(file_path, "PNG")
    
    if success:
        # 절대 경로를 보여주면 어디에 저장되었는지 확인하기 쉽습니다.
        QMessageBox.information(widget, "성공", f"스크린샷이 저장되었습니다:\n{file_path}")
    else:
        QMessageBox.warning(widget, "실패", "스크린샷 저장에 실패했습니다.")