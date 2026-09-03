@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   마케팅그룹 운영 대시보드 실행
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.11 이상을 설치한 뒤 다시 실행해주세요.
    echo 설치 시 "Add Python to PATH"에 반드시 체크하세요.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/4] 처음 실행입니다. 가상환경을 만드는 중입니다... (1~2분 소요)
    python -m venv .venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo [2/4] 필요한 패키지를 확인/설치하는 중입니다...
python -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인해주세요.
    pause
    exit /b 1
)

if not exist "data\dashboard.duckdb" (
    echo [3/4] 최초 실행 - data\raw\*.csv 를 DuckDB에 적재합니다...
    python -c "from src import database as db, transformation as t; t.build_all(db.get_connection())"
)

echo [4/4] 대시보드를 실행합니다. 잠시 후 브라우저가 자동으로 열립니다...
echo (종료하려면 이 창에서 Ctrl+C 를 누르거나 창을 닫으세요)
echo.

python -m streamlit run app.py

pause
