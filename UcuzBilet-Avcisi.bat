@echo off
chcp 65001 >nul
setlocal
title UcuzBilet Avcisi
cd /d "%~dp0"

set "VENV_UV=.venv\Scripts\uvicorn.exe"
set "URL=http://127.0.0.1:8787"

if not exist "%VENV_UV%" (
    echo [1/3] Sanal ortam kuruluyor...
    python -m venv .venv
    if errorlevel 1 (
        echo HATA: Python bulunamadi. Python 3.11+ yukleyin.
        pause
        exit /b 1
    )
    echo [2/3] Paketler yukleniyor...
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    if errorlevel 1 (
        echo HATA: Paket kurulumu basarisiz.
        pause
        exit /b 1
    )
    echo [3/3] Chromium indiriliyor...
    playwright install chromium
)

echo Eski sunucu varsa kapatiliyor...
powershell -NoProfile -Command ^
  "$c = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue; if ($c) { $c | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"
timeout /t 2 /nobreak >nul

echo UcuzBilet Avcisi sunucusu baslatiliyor...
start "UcuzBilet Avcisi - Sunucu" cmd /k "cd /d %~dp0 && .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8787"

echo Sunucu hazirlaniyor...
set /a tries=0
:wait_loop
set /a tries+=1
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command ^
  "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto open_browser
if %tries% lss 25 goto wait_loop

echo HATA: Sunucu baslamadi. "UcuzBilet Avcisi - Sunucu" penceresindeki hatayi kontrol edin.
pause
exit /b 1

:open_browser
start "" "%URL%"
echo Tamam. Bu pencereyi kapatabilirsiniz.
echo Sunucuyu durdurmak icin "UcuzBilet Avcisi - Sunucu" penceresini kapatın.
timeout /t 3 >nul
exit /b 0
