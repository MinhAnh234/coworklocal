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
rem  duoc no. Neu khong, ta tro mot junction toi no.
rem
rem  Junction duoc TAO LAI moi lan chay, khong phai chi khi thieu. Ban truoc chi
rem  hoi "co ton tai khong", nen mot junction con lai tu checkout KHAC van duoc
rem  dung lai im lang: run.bat nam trong thu muc nay nhung ung dung chay tu thu
rem  muc kia. Trieu chung la "sua code xong chay van y nguyen" — mat rat lau moi
rem  nghi ra, vi khong co gi bao loi ca. Tao lai ton vai mili giay va bo han ca
rem  lop loi do. install.bat cung lam dung nhu vay.
rem --------------------------------------------------------------------------
rem  Junction rieng cho TUNG thu muc ma nguon, khong dung chung mot cai.
rem
rem  Ban truoc dung dung mot duong dan %LAUNCHER%\cowork_local cho ca may. Hai
rem  ban checkout thi tranh nhau no: cai chay sau tro junction ve minh, va tien
rem  trinh con cua cai chay truoc (may chu MCP MS365, sinh ra sau khi app da mo)
rem  se import ma nguon cua cai kia. Rat kho lan ra, vi khong co gi bao loi.
rem
rem  Khoa lay tu bam SHA1 cua duong dan tuyet doi (normcase, nen khong phan biet
rem  hoa thuong nhu Windows). Moi thu muc ma nguon co mot khoa on dinh, khong
rem  bao gio dung chung.
for %%I in ("%REPO%") do set "REPO_NAME=%%~nxI"
if /I "%REPO_NAME%"=="cowork_local" (
    for %%I in ("%REPO%\..") do set "PKGPATH=%%~fI"
) else (
    set "REPO_KEY="
    for /f "delims=" %%K in ('!RUNPY! -c "import hashlib,os,sys;print(hashlib.sha1(os.path.normcase(os.path.abspath(sys.argv[1])).encode()).hexdigest()[:10])" "%REPO%" 2^>nul') do set "REPO_KEY=%%K"
    if not defined REPO_KEY set "REPO_KEY=default"
    set "PKGPATH=%LAUNCHER%\!REPO_KEY!"
    if not exist "!PKGPATH!" mkdir "!PKGPATH!" >nul 2>&1
    if exist "!PKGPATH!\cowork_local" rmdir "!PKGPATH!\cowork_local" >nul 2>&1
    mklink /J "!PKGPATH!\cowork_local" "%REPO%" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [LOI] Khong tao duoc lien ket thu muc:
        echo        "!PKGPATH!\cowork_local"  ->  "%REPO%"
        echo.
        echo        Thuong gap khi ma nguon nam tren o mang, hoac tren o dia dinh
        echo        dang khong phai NTFS - junction khong tro sang duoc.
        echo        Cach khac: chep ma nguon ve o dia trong may, hoac doi ten thu
        echo        muc ma nguon thanh  cowork_local  la khong can junction nua.
        echo.
        pause
        exit /b 1
    )
)

rem  Chot lai: goi phai THAT SU nhin thay duoc qua duong dan vua dung. Khong co
rem  buoc nay thi mot junction hong chi hien ra duoi dang loi Python kho hieu
rem  ("'cowork_local' is a package and cannot be directly executed").
if not exist "!PKGPATH!\cowork_local\__main__.py" (
    echo.
    echo  [LOI] Khong tim thay  cowork_local\__main__.py  qua duong dan:
    echo        "!PKGPATH!"
    echo.
    echo        Ma nguon o "%REPO%" bi thieu file, hoac lien ket dang tro nham cho.
    echo        Chay  install.bat  de dung lai tu dau.
    echo.
    pause
    exit /b 1
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
