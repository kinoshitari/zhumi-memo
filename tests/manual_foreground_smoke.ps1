Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class ForegroundProbe
{
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    public static uint ForegroundProcessId()
    {
        uint processId;
        GetWindowThreadProcessId(GetForegroundWindow(), out processId);
        return processId;
    }
}
"@

$target = Get-Process -Name ZhumiMemo -ErrorAction Stop | Select-Object -First 1
$form = New-Object System.Windows.Forms.Form
$form.Text = "ZhumiMemo foreground smoke fixture"
$form.Size = New-Object System.Drawing.Size(480, 180)
$form.StartPosition = "CenterScreen"
$form.TopMost = $true
$form.Show()
$form.Activate()

for ($i = 0; $i -lt 10; $i++) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 50
}

$before = [ForegroundProbe]::ForegroundProcessId()
[System.Windows.Forms.SendKeys]::SendWait("%v")

for ($i = 0; $i -lt 30; $i++) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 50
}

$after = [ForegroundProbe]::ForegroundProcessId()
$visibleWindow = Get-Process -Id $target.Id -ErrorAction Stop
$visibleHandle = $visibleWindow.MainWindowHandle
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")
for ($i = 0; $i -lt 10; $i++) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 50
}
$hiddenAfterTest = (Get-Process -Id $target.Id -ErrorAction Stop).MainWindowHandle -eq 0
$form.Close()

[pscustomobject]@{
    FixturePid = $PID
    ForegroundBefore = $before
    AppPid = $target.Id
    ForegroundAfter = $after
    ForegroundTransferred = ($before -eq $PID -and $after -eq $target.Id)
    AppMainWindowHandle = $visibleHandle
    AppResponding = $visibleWindow.Responding
    HiddenAfterEscape = $hiddenAfterTest
} | Format-List

if ($before -ne $PID -or $after -ne $target.Id) {
    exit 1
}
