# =============================================================================
# lv_start_nigel_chat.ps1 - starts the Nigel chat window (LVNigelChat.exe) without
# a person, the way LabVIEW's menu plug-in does: with BOTH --lv-version and
# --lv-bitness. Optional last step of skill lv-restart (05 rule 99). Never kills.
# =============================================================================
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File lv_start_nigel_chat.ps1 -Version 26.3 -Bitness x86 [-WaitSeconds 10] [-AddonRoot <folder>] [-Check]
#   -Version     the running LabVIEW's version as the add-on folder names it (e.g. 26.3 for 2026 Q3)
#   -Bitness     x86 (32-bit LabVIEW, under "Program Files (x86)") or x64
#   -AddonRoot   default <Program Files>\NI\LVAddons\lvai (the 64-bit Program Files, also from 32-bit PowerShell)
#   -Check       print the exe found and the exact command; start nothing
# Output: exe path, the command, the new PID, after WaitSeconds: exited or not, and every
#   top-level window of that PID (class, visible, title); a message box (#32770) is flagged.
# Exit: 0 started and a window other than a message box is up (or -Check, or already running);
#   1 the process exited or a message box is up (STOP and report; lv_press_ok.ps1 may close a box
#   of THIS PID only); 2 exe not found.
# Never run LVNigelChat.exe without both options: --help or a missing option does not exit and
# leaves a modal "Object reference not set to an instance of an object." box (H21).
# If LVNigelChat already runs, nothing is started (one chat per LabVIEW). Ported from H21_start_chat.ps1.
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][ValidateSet('x86', 'x64')][string]$Bitness,
    [int]$WaitSeconds = 10,
    [string]$AddonRoot = '',
    [switch]$Check
)

if (-not $AddonRoot) {
    $pf = if ($env:ProgramW6432) { $env:ProgramW6432 } else { $env:ProgramFiles }
    $AddonRoot = Join-Path $pf 'NI\LVAddons\lvai'
}
$exe = Join-Path $AddonRoot "$Version\resource\AI\LVNigelChat\LVNigelChat.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    "STOP: not found: $exe"
    $have = Get-ChildItem -LiteralPath $AddonRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }
    "versions under ${AddonRoot}: $($have -join ', ')"
    exit 2
}
"exe     $exe"
"command Start-Process `"$exe`" -ArgumentList '--lv-version','$Version','--lv-bitness','$Bitness'"

$running = @(Get-Process LVNigelChat -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    $running | ForEach-Object { "already running: LVNigelChat pid $($_.Id) title [$($_.MainWindowTitle)]; nothing started" }
    exit 0
}
if ($Check) { 'check: nothing started'; exit 0 }

Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public static class NigelWins {
 public delegate bool P(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumWindows(P f, IntPtr l);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 public static List<string> Of(uint want) { var r = new List<string>();
  EnumWindows((h, l) => { uint pid; GetWindowThreadProcessId(h, out pid);
   if (pid == want) { var c = new StringBuilder(256); var t = new StringBuilder(512);
    GetClassName(h, c, 256); GetWindowText(h, t, 512);
    r.Add(h.ToInt64() + "\t" + c + "\t" + IsWindowVisible(h) + "\t" + t); } return true; }, IntPtr.Zero);
  return r; } }
"@

$p = Start-Process -FilePath $exe -ArgumentList '--lv-version', $Version, '--lv-bitness', $Bitness -PassThru
"started pid $($p.Id) at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Start-Sleep -Seconds $WaitSeconds
$p.Refresh()
if ($p.HasExited) { "STOP: pid $($p.Id) exited, code $($p.ExitCode)"; exit 1 }
"running pid $($p.Id) responding $($p.Responding)"
'--- top-level windows (hwnd, class, visible, title)'
$box = $false; $main = $false
foreach ($w in [NigelWins]::Of([uint32]$p.Id)) {
    $f = $w.Split("`t")
    if ($f[2] -ne 'True') { continue }
    $flag = ''
    if ($f[1] -eq '#32770') { $flag = '  <- MESSAGE BOX'; $box = $true } else { $main = $true }
    "$w$flag"
}
if ($box) { 'STOP: a message box is up; report its text (lv_press_ok.ps1 -ProcId <pid> -Check)'; exit 1 }
if (-not $main) { 'no visible window yet; check again later'; exit 0 }
exit 0
