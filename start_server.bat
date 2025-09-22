@echo off
REM 設定編碼為 UTF-8
chcp 65001 >nul

REM 設定專案路徑
set PROJECT_PATH=D:\Project\NuECS

REM 檢查專案目錄是否存在
if not exist "%PROJECT_PATH%" (
    echo 錯誤：專案目錄不存在 %PROJECT_PATH%
    pause
    exit /b 1
)

REM 切換到專案目錄
echo 切換到專案目錄：%PROJECT_PATH%
cd /d "%PROJECT_PATH%"

REM 檢查虛擬環境是否存在
if not exist ".venv\Scripts\activate.bat" (
    echo 錯誤：虛擬環境不存在，請先建立虛擬環境
    echo 執行：python -m venv .venv
    pause
    exit /b 1
)

REM 啟用虛擬環境
echo 啟用虛擬環境...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo 錯誤：無法啟用虛擬環境
    pause
    exit /b 1
)

REM 檢查 run.py 是否存在
if not exist "run.py" (
    echo 錯誤：找不到 run.py 檔案
    pause
    exit /b 1
)

REM 顯示 Python 版本和路徑（除錯用）
echo Python 版本：
python --version
echo Python 路徑：
where python

REM 啟動主程式
echo 啟動 API 伺服器...
python run.py

REM 如果程式異常結束，暫停以查看錯誤訊息
if errorlevel 1 (
    echo.
    echo 程式執行時發生錯誤，錯誤碼：%errorlevel%
    pause
)

echo.
echo 程式已結束
pause