# =============================================================================
# lv_close.ps1 - closes the one LabVIEW IDE cleanly (CloseMainWindow + WaitForExit
# with a timeout) and prints the timing; never kills it. The close step of the
# LabVIEW restart (session/restart.md; pilot rule 96). Run lv_windows.ps1 first.
# =============================================================================
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File lv_close.ps1 [-ProcessName LabVIEW] [-TimeoutSeconds 20] [-Check]
#   -Check  dry run: shows the process it would close and exits; sends nothing
# Output: pid, close start time, CloseMainWindow result, WaitForExit result after <s> s, the exit
#   time (taken by this script: Process.ExitTime reads null after the exit, H19), ExitCode.
# Exit: 0 exited; 1 not exited within the timeout: CloseMainWindow False = LabVIEW did not take the
#   close message (busy running a VI Server helper, or a modal dialog); True = a dialog came up after
#   the request. STOP, check with lv_windows.ps1 and wait_lv_idle.ps1, report; never kill.
#   2 no LabVIEW process or more than one.
# Only with the user's go-ahead for this restart, the project closed with projectPath (pilot rule 95).
param(
    [string]$ProcessName = 'LabVIEW',
    [int]$TimeoutSeconds = 20,
    [switch]$Check
)

$p = @(Get-Process $ProcessName -ErrorAction SilentlyContinue)
if ($p.Count -ne 1) { "STOP: $ProcessName process count $($p.Count) (0 = not running; >1 = ask which one)"; exit 2 }
$p = $p[0]
"pid $($p.Id) StartTime $($p.StartTime.ToString('yyyy-MM-dd HH:mm:ss.fff')) title [$($p.MainWindowTitle)]"
if ($Check) { "check: would send CloseMainWindow to pid $($p.Id) and wait $TimeoutSeconds s; nothing sent"; exit 0 }

"close start $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff')"
$sw = [Diagnostics.Stopwatch]::StartNew()
$sent = $p.CloseMainWindow()
$exited = $p.WaitForExit($TimeoutSeconds * 1000)
$sw.Stop()
$end = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
"CloseMainWindow returned $sent"
"WaitForExit $exited after $([math]::Round($sw.Elapsed.TotalSeconds, 2)) s at $end"
if ($exited) {
    $code = try { $p.ExitCode } catch { 'n/a' }
    "exited at $end (own clock) ExitCode $code"
    exit 0
}
if ($sent) { "STOP: LabVIEW did not exit within $TimeoutSeconds s; CloseMainWindow returned True: a dialog came up after the close request (the user answers it)." }
else { "STOP: LabVIEW did not exit within $TimeoutSeconds s; CloseMainWindow returned False: LabVIEW did not take the close message (busy running a VI Server helper, or a modal dialog)." }
"Check with lv_windows.ps1 (dialogs) and wait_lv_idle.ps1 (CPU); never kill LabVIEW; report."
exit 1
