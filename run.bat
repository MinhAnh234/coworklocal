@echo off
rem ===========================================================================
rem  Cowork-Local BamBOO - chay ung dung
rem
rem  Bam dup vao file nay la xong.
rem
rem  Lan dau tien phai chay install.bat truoc.
rem
rem  Tham so truyen vao duoc chuyen thang cho QApplication (xem app.py::run),
rem  nen dung duoc cac co cua Qt, vi du:  run.bat -style Fusion
rem ===========================================================================
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Cowork-Local BamBOO

set "REPO=%~dp0"
set "REPO=%REPO:~0,-1%"
set "APPHOME=%LOCALAPPDATA%\CoworkLocal"
set "VENV=%APPHOME%\venv"
set "LAUNCHER=%APPHOME%\launcher"

rem --------------------------------------------------------------------------
rem  1. Chon trinh thong dich
rem
rem  Uu tien moi truong ao do install.bat dung. Khong co thi quay ve Python cua
rem  he thong — nguoi dung co the da chay "install.bat --system".
rem --------------------------------------------------------------------------
rem  Duong dan luon duoc boc trong dau nhay: %LOCALAPPDATA% co the chua khoang
rem  trang neu ten dang nhap co khoang trang.
if exist "%VENV%\Scripts\python.exe" (
    set "RUNPY="%VENV%\Scripts\python.exe""
) else (
    set "RUNPY="
    for /f "delims=" %%P in ('where py 2^>nul') do if not defined RUNPY set "RUNPY="%%P" -3"
    if not defined RUNPY (
        for /f "delims=" %%P in ('where python 2^>nul') do if not defined RUNPY set "RUNPY="%%P""
    )
)

if not defined RUNPY (
    echo.
    echo  [LỖI] Không tìm thấy Python. Chạy  install.bat  trước đã.
    echo.
    pause
    exit /b 1
)

rem  Chua co moi truong ao thi kiem xem Python he thong co du thu vien khong.
rem  Khong kiem thi nguoi dung chi nhan duoc mot ModuleNotFoundError tho, chang
rem  biet la phai chay install.bat.
if not exist "%VENV%\Scripts\python.exe" (
    !RUNPY! -c "import PySide6" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [LỖI] Thư viện chưa được cài. Chạy  install.bat  trước đã.
        echo.
        pause
        exit /b 1
    )
)

rem --------------------------------------------------------------------------
rem  2. Duong dan de import duoc goi "cowork_local"
rem
rem  Thu muc ma nguon phai mang dung ten "cowork_local" thi Python moi import
rem  duoc no. Neu khong, install.bat da tao mot junction; o day chi kiem tra va
rem  tu dung lai neu no bi xoa — de nguoi dung khong phai chay lai install.bat
rem  chi vi mot thu muc tam bi don.
rem --------------------------------------------------------------------------
for %%I in ("%REPO%") do set "REPO_NAME=%%~nxI"
if /I "%REPO_NAME%"=="cowork_local" (
    for %%I in ("%REPO%\..") do set "PKGPATH=%%~fI"
) else (
    if not exist "%LAUNCHER%\cowork_local" (
        if not exist "%LAUNCHER%" mkdir "%LAUNCHER%" >nul 2>&1
        mklink /J "%LAUNCHER%\cowork_local" "%REPO%" >nul 2>&1
        if errorlevel 1 (
            echo.
            echo  [LỖI] Không tạo được liên kết thư mục. Chạy  install.bat  lại.
            echo.
            pause
            exit /b 1
        )
    )
    set "PKGPATH=%LAUNCHER%"
)

rem --------------------------------------------------------------------------
rem  3. Chay
rem
rem  Dat thu muc lam viec o goc ma nguon va PYTHONPATH tro toi thu muc CHA cua
rem  goi — dung cach CI dang chay (.gitea/workflows/ci.yaml). Tien trinh con
rem  (may chu MCP MS365) thua ke PYTHONPATH nay nen cung import duoc.
rem --------------------------------------------------------------------------
if defined PYTHONPATH (
    set "PYTHONPATH=!PKGPATH!;%PYTHONPATH%"
) else (
    set "PYTHONPATH=!PKGPATH!"
)
set "PYTHONIOENCODING=utf-8"
cd /d "%REPO%"

rem --------------------------------------------------------------------------
rem  4. An cua so console trong luc chay
rem
rem  App la GUI (Qt), khong can console — nhung no chia se console cua chinh
rem  cmd nay (khong tu mo cua so rieng), nen cua so den cua run.bat cu the
rem  hien suot phien lam viec neu khong lam gi. An no ngay truoc khi chay, roi
rem  chi hien lai NEU app thoat loi, de thong bao loi ben duoi van doc duoc.
rem --------------------------------------------------------------------------
set "CONSOLE_VIS=%REPO%\scripts\console_visibility.ps1"
if exist "%CONSOLE_VIS%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%CONSOLE_VIS%" -Mode 0 >nul 2>&1
)

!RUNPY! -m cowork_local %*
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    if exist "%CONSOLE_VIS%" (
        powershell -NoProfile -ExecutionPolicy Bypass -File "%CONSOLE_VIS%" -Mode 5 >nul 2>&1
    )
    echo.
    echo  Ứng dụng thoát với mã lỗi %RC%. Xem thông báo ở trên.
    echo.
    pause
)
exit /b %RC%
