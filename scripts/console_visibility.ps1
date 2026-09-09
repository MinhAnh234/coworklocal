<#
.SYNOPSIS
    Ẩn/hiện cửa sổ console hiện tại — dùng bởi run.bat để không hiện cửa sổ
    cmd đen suốt phiên chạy app (app là GUI Qt, không cần console), nhưng vẫn
    hiện lại được nếu app thoát lỗi để người dùng đọc thông báo.

.PARAMETER Mode
    0 = ẩn (SW_HIDE), 5 = hiện lại (SW_SHOW).
#>
param(
    [int]$Mode = 0
)

Add-Type -Name Win32 -Namespace CoworkLocalNative -MemberDefinition @"
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
[DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
"@

$hwnd = [CoworkLocalNative.Win32]::GetConsoleWindow()
if ($hwnd -ne [IntPtr]::Zero) {
    [CoworkLocalNative.Win32]::ShowWindow($hwnd, $Mode) | Out-Null
}
