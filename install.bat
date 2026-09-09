@echo off
rem ===========================================================================
rem  Cowork-Local BamBOO - cai dat thu vien Python (chay MOT lan)
rem
rem  Cach dung:
rem      install.bat              cai vao moi truong ao rieng (khuyen dung)
rem      install.bat --system     cai thang vao Python dang co, khong dung venv
rem      install.bat --force      dung lai moi truong ao tu dau
rem
rem  Cai gi va cai o dau:
rem      %LOCALAPPDATA%\CoworkLocal\venv       moi truong ao
rem      %LOCALAPPDATA%\CoworkLocal\launcher\<khoa>  lien ket de import duoc goi
rem                                            (mot khoa cho moi thu muc ma nguon)
rem
rem  Vi sao KHONG dat venv trong repo: cac cong chat luong
rem  (scripts/check_orphan_modules.py, check_imports.py) quet TOAN BO cay thu
rem  muc chu khong doc .gitignore, nen mot thu muc .venv o day se bien vai nghin
rem  module cua thu vien thanh "ma production khong ai import" va lam cong do.
rem ===========================================================================
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1

set "REPO=%~dp0"
set "REPO=%REPO:~0,-1%"
set "APPHOME=%LOCALAPPDATA%\CoworkLocal"
set "VENV=%APPHOME%\venv"
set "LAUNCHER=%APPHOME%\launcher"

set "USE_SYSTEM=0"
set "FORCE=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--system"  set "USE_SYSTEM=1" & shift & goto parse_args
if /I "%~1"=="--force"   set "FORCE=1"      & shift & goto parse_args
if /I "%~1"=="-h"        goto usage
if /I "%~1"=="--help"    goto usage
echo [LOI] Khong hieu tham so: %~1
goto usage
:args_done

echo.
echo ===========================================================================
echo  Cowork-Local BamBOO — cài đặt
echo ===========================================================================
echo  Mã nguồn : %REPO%
echo  Cài vào  : %APPHOME%
echo.

rem --------------------------------------------------------------------------
rem  1. Tim Python
rem
rem  Uu tien "py -3" chu khong phai "python": tren Windows 11, python.exe trong
rem  WindowsApps thuong chi la lien ket mo Microsoft Store chu khong phai
rem  Python that.
rem --------------------------------------------------------------------------
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python -c "import sys" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [LỖI] Không tìm thấy Python trên máy này.
    echo        Cài Python 3.11 trở lên từ https://www.python.org/downloads/
    echo        và nhớ tích "Add python.exe to PATH" khi cài.
    goto fail
)

for /f "delims=" %%V in ('%PY% -c "import sys;print('%%d.%%d'%%sys.version_info[:2])" 2^>nul') do set "PYVER=%%V"
echo  [1/5] Python %PYVER%  (%PY%)

%PY% -c "import sys;raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [LỖI] Cần Python 3.11 trở lên, máy đang có %PYVER%.
    goto fail
)

rem --------------------------------------------------------------------------
rem  2. Moi truong ao
rem --------------------------------------------------------------------------
if "%USE_SYSTEM%"=="1" (
    echo  [2/5] Bỏ qua môi trường ảo — cài thẳng vào Python đang có ^(--system^)
    set "PIP=%PY% -m pip"
    goto deps
)

if "%FORCE%"=="1" if exist "%VENV%" (
    echo  [2/5] Xoá môi trường ảo cũ...
    rmdir /s /q "%VENV%" 2>nul
)

rem  Chi kiem file python.exe co ton tai la khong du: mot venv dung lai tu ban
rem  Python da bi nang cap hoac xoa van con nguyen file do, nhung chay vao la loi
rem  ngay. Goi thu mot lenh that de biet no con song.
set "VENV_OK=0"
if exist "%VENV%\Scripts\python.exe" (
    "%VENV%\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "VENV_OK=1"
)

if "!VENV_OK!"=="1" (
    echo  [2/5] Môi trường ảo đã có — dùng lại
) else (
    if exist "%VENV%" (
        echo  [2/5] Môi trường ảo cũ không chạy được — dựng lại từ đầu...
        rmdir /s /q "%VENV%" 2>nul
    ) else (
        echo  [2/5] Tạo môi trường ảo...
    )
    %PY% -m venv "%VENV%"
    if errorlevel 1 (
        echo [LỖI] Không tạo được môi trường ảo.
        echo        Thử lại với:  install.bat --system
        goto fail
    )
)
set "PIP="%VENV%\Scripts\python.exe" -m pip"

rem --------------------------------------------------------------------------
rem  3. Cai thu vien
rem --------------------------------------------------------------------------
:deps
echo  [3/5] Cập nhật pip...
%PIP% install --disable-pip-version-check --quiet --upgrade pip
if errorlevel 1 echo        ^(bỏ qua — pip cũ vẫn dùng được^)

echo  [3/5] Cài thư viện từ requirements.txt  ^(PySide6 khá nặng, chờ vài phút^)...
%PIP% install --disable-pip-version-check -r "%REPO%\requirements.txt"
if errorlevel 1 (
    echo [LỖI] Cài thư viện thất bại.
    echo        Nếu máy qua proxy công ty, đặt biến môi trường HTTPS_PROXY rồi chạy lại.
    goto fail
)

rem --------------------------------------------------------------------------
rem  4. Lien ket de goi import duoc dung ten
rem
rem  Ma nguon phai import duoc duoi dung ten "cowork_local". Thu muc nay ten la
rem  "%~nx0"'s parent — neu no khong phai "cowork_local" thi ca
rem  "python -m cowork_local" lan "python __main__.py" deu bao
rem  ModuleNotFoundError, va tien trinh con chay may chu MCP MS365
rem  (state.py: python -m cowork_local.mcp_servers.ms365_server) cung hong theo.
rem
rem  Junction giai quyet ca hai ma khong phai doi ten thu muc lam viec, khong
rem  phai sua mot dong code nao, va khong can quyen quan tri.
rem --------------------------------------------------------------------------
for %%I in ("%REPO%") do set "REPO_NAME=%%~nxI"
if /I "%REPO_NAME%"=="cowork_local" (
    echo  [4/5] Thư mục đã đúng tên "cowork_local" — không cần liên kết
    goto smoke
)

rem  Junction rieng cho TUNG thu muc ma nguon. Ban truoc dung dung mot duong
rem  dan cho ca may, nen hai ban checkout tranh nhau: cai chay sau tro junction
rem  ve minh, va tien trinh con cua cai chay truoc (may chu MCP MS365) se import
rem  ma nguon cua cai kia.
set "REPO_KEY="
for /f "delims=" %%K in ('%PY% -c "import hashlib,os,sys;print(hashlib.sha1(os.path.normcase(os.path.abspath(sys.argv[1])).encode()).hexdigest()[:10])" "%REPO%" 2^>nul') do set "REPO_KEY=%%K"
if not defined REPO_KEY set "REPO_KEY=default"
set "PKGROOT=%LAUNCHER%\!REPO_KEY!"

rem  Don junction dung chung cua ban cu: de lai la mot cai bay — mot run.bat cu
rem  o thu muc khac se dung lai no va chay nham ma nguon. rmdir KHONG co /s: voi
rem  junction thi no xoa lien ket, khong xoa noi dung dich.
if exist "%LAUNCHER%\cowork_local" rmdir "%LAUNCHER%\cowork_local" >nul 2>&1

if not exist "!PKGROOT!" mkdir "!PKGROOT!" >nul 2>&1
if exist "!PKGROOT!\cowork_local" rmdir "!PKGROOT!\cowork_local" >nul 2>&1
mklink /J "!PKGROOT!\cowork_local" "%REPO%" >nul
if errorlevel 1 (
    echo [LỖI] Không tạo được liên kết thư mục.
    echo        Thư mục "%REPO_NAME%" không phải tên gói Python hợp lệ nên
    echo        ứng dụng không import được chính nó. Cách khác: đổi tên thư mục
    echo        mã nguồn thành "cowork_local".
    goto fail
)
echo  [4/5] Đã tạo liên kết: !PKGROOT!\cowork_local

rem --------------------------------------------------------------------------
rem  5. Chay thu mot lan
rem --------------------------------------------------------------------------
:smoke
if "%USE_SYSTEM%"=="1" (set "RUNPY=%PY%") else (set "RUNPY="%VENV%\Scripts\python.exe"")
if /I "%REPO_NAME%"=="cowork_local" (
    for %%I in ("%REPO%\..") do set "PKGPATH=%%~fI"
) else (
    set "PKGPATH=!PKGROOT!"
)

echo  [5/5] Kiểm tra lại...
set "PYTHONPATH=!PKGPATH!"
rem  Kiem ca DANH TINH, khong chi kiem import duoc: neu tren sys.path con mot thu
rem  muc khac cung ten "cowork_local" (mot ban checkout cu chang han) thi lenh
rem  import van chay tot, va ca buoc kiem tra nay se xanh trong khi ung dung
rem  dang chay tu ma nguon KHAC. Duong dan truyen qua bien moi truong de khoi
rem  phai boc dau nhay long nhau trong chuoi -c.
set "EXPECT_REPO=%REPO%"
%RUNPY% -c "import os,sys,cowork_local,PySide6; p=os.path.realpath(os.path.dirname(cowork_local.__file__)); e=os.path.realpath(os.environ['EXPECT_REPO']); print('        cowork_local + PySide6 nap duoc'); print('        goi doc tu: '+p); sys.exit(0 if p==e else 3)"
if errorlevel 3 (
    echo [LỖI] Gói import được, nhưng KHÔNG phải từ thư mục mã nguồn này:
    echo        mong đợi: %REPO%
    echo        Trên PYTHONPATH hoặc site-packages đang có một "cowork_local" khác
    echo        chen lên trước. Gỡ nó đi rồi chạy lại install.bat.
    goto fail
)
if errorlevel 1 (
    echo [LỖI] Cài xong nhưng vẫn chưa import được gói.
    goto fail
)

echo.
echo ===========================================================================
echo  XONG. Từ giờ chỉ cần bấm đúp vào  run.bat
echo ===========================================================================
echo.
pause
exit /b 0

:usage
echo.
echo  install.bat [--system] [--force]
echo.
echo    --system   cài thẳng vào Python đang có, không tạo môi trường ảo
echo    --force    xoá môi trường ảo cũ rồi tạo lại từ đầu
echo.
pause
exit /b 2

:fail
echo.
echo  Cài đặt KHÔNG thành công. Xem thông báo lỗi ở trên.
echo.
pause
exit /b 1
