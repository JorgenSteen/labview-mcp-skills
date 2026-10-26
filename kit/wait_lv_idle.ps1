# =============================================================================
# wait_lv_idle.ps1 - waits until LabVIEW's CPU time shows it idle, with no LabVIEW
# call: tells "still busy" from "idle" after a DeadlineExceeded or a hung call,
# when every labview-mcp call (lvai_status too) would only add to the block.
# =============================================================================
# Usage (PowerShell, read-only, never closes, kills or presses anything):
#   powershell -NoProfile -ExecutionPolicy Bypass -File wait_lv_idle.ps1
#       [-ProcessName LabVIEW] [-WindowSeconds 30] [-IdleCpuSeconds 1] [-QuietWindows 3]
#       [-MaxMinutes 90] [-LogFile <path>] [-Once] [-Check]
#   Samples the LabVIEW process's CPU time over windows of -WindowSeconds. A window is quiet when
#   LabVIEW used less than -IdleCpuSeconds of CPU in it; -QuietWindows quiet windows in a row = idle.
#   Each window prints one line: time, CPU seconds used, and the titles of LabVIEW's visible windows
#   (VI panels, dialogs), so a dialog that comes up while waiting shows in the log.
#   -Once     one window only: print it and exit 0 (quiet) or 1 (busy). Two -Once runs at least
#             15 s apart are the "sampled twice" check of knowledge/labview-mcp.md.
#   -LogFile  also append every line to this file (absolute, long-form path); default: console only.
#   -Check    print the process found and the settings; samples and waits nothing.
# Exit: 0 idle (or -Check); 1 still busy at -MaxMinutes (or -Once busy); 2 no LabVIEW process or
#   more than one, or LabVIEW exited while waiting.
# Idle is not "safe": a modal dialog leaves LabVIEW idle and the service blocked. Run lvai_labview_state
#   after an idle verdict. Provenance: ported from the skills audit's scratch wait script (runs R1, R3).
param(
    [string]$ProcessName = 'LabVIEW',
    [int]$WindowSeconds = 30,
    [double]$IdleCpuSeconds = 1,
    [int]$QuietWindows = 3,
    [double]$MaxMinutes = 90,
    [string]$LogFile = '',
    [switch]$Once,
    [switch]$Check
)

function Out-Line([string]$s) {
    $s
    if ($LogFile) { $s | Out-File -FilePath $LogFile -Append -Encoding utf8 }
}

$lv = @(Get-Process $ProcessName -ErrorAction SilentlyContinue)
if ($lv.Count -ne 1) { Out-Line "$(Get-Date -Format HH:mm:ss) STOP: $ProcessName process count $($lv.Count) (0 = not running; >1 = ask which one)"; exit 2 }
$p = $lv[0]
if ($Check) {
    "$ProcessName PID $($p.Id) StartTime $($p.StartTime.ToString('yyyy-MM-dd HH:mm:ss')) CPU $([math]::Round($p.CPU, 1)) s"
    "settings: window $WindowSeconds s, idle below $IdleCpuSeconds CPU s per window, $QuietWindows quiet windows, max $MaxMinutes min, once $([bool]$Once), log [$LogFile]"
    exit 0
}

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class LvIdleWin {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
}
"@

function Get-VisibleTitles([uint32]$procId) {
    $script:titles = New-Object System.Collections.ArrayList
    $cb = [LvIdleWin+EnumProc]{ param($h, $l)
        $wp = [uint32]0; [void][LvIdleWin]::GetWindowThreadProcessId($h, [ref]$wp)
        if ($wp -eq $procId -and [LvIdleWin]::IsWindowVisible($h)) {
            $sb = New-Object System.Text.StringBuilder 512; [void][LvIdleWin]::GetWindowText($h, $sb, 512)
            if ($sb.Length -gt 0 -and $sb.ToString() -ne 'LabVIEW') { [void]$script:titles.Add($sb.ToString()) }
        }
        return $true }
    [void][LvIdleWin]::EnumWindows($cb, [IntPtr]::Zero)
    return ,$script:titles
}

Out-Line "$(Get-Date -Format HH:mm:ss) $ProcessName PID $($p.Id): window $WindowSeconds s, idle below $IdleCpuSeconds CPU s, $QuietWindows quiet windows"
$quiet = 0; $t0 = Get-Date
while (((Get-Date) - $t0).TotalMinutes -lt $MaxMinutes) {
    $c0 = $p.CPU
    Start-Sleep -Seconds $WindowSeconds
    $p.Refresh()
    if ($p.HasExited) { Out-Line "$(Get-Date -Format HH:mm:ss) STOP: $ProcessName exited while waiting"; exit 2 }
    $d = [math]::Round($p.CPU - $c0, 1)
    $titles = Get-VisibleTitles ([uint32]$p.Id)
    Out-Line "$(Get-Date -Format HH:mm:ss) cpu=$d s/$WindowSeconds s windows=[$($titles -join ' | ')]"
    if ($d -lt $IdleCpuSeconds) { $quiet++ } else { $quiet = 0 }
    if ($Once) {
        if ($quiet) { Out-Line "$(Get-Date -Format HH:mm:ss) QUIET (one window; sample again at least 15 s later)"; exit 0 }
        Out-Line "$(Get-Date -Format HH:mm:ss) BUSY"; exit 1
    }
    if ($quiet -ge $QuietWindows) { Out-Line "$(Get-Date -Format HH:mm:ss) IDLE"; exit 0 }
}
Out-Line "$(Get-Date -Format HH:mm:ss) STILL BUSY after $MaxMinutes min: make no LabVIEW call; report"
exit 1
