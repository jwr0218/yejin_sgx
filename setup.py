from setuptools import setup, find_packages

setup(
    name="yejin_request",  # pip list에 표시될 패키지 이름
    version="0.1.0",
    # -----------------------------------------------------------
    # [핵심 수정] 특정 폴더명을 지정하지 말고 find_packages() 사용
    # 이렇게 하면 __init__.py가 있는 폴더(예: app)를 자동으로 찾습니다.
    # -----------------------------------------------------------
    packages=find_packages(), 
    install_requires=[
        "requests",
        "selenium",
        "datetime",
        "PyQt6"
    ],
)