# =============================================================================
# lv_press_ok.ps1 - presses OK on a message box (#32770) of ONE given process, by
# posting BM_CLICK to its "OK" button, then waits to see whether the process exits.
# For a box our own probe raised (H21: LVNigelChat --help). Refuses LabVIEW's PID.
# =============================================================================
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File lv_press_ok.ps1 -ProcId <pid> [-Hwnd <box hwnd>] [-WaitSeconds 10] [-AllowLabVIEW] [-Check]
#   -ProcId        the process that owns the box (required; never a guess)
#   -Hwnd          which box, when the process shows more than one
#   -AllowLabVIEW  needed to press a box of a LabVIEW.exe process (a LabVIEW dialog is the user's
#                  to answer; only with the user's go-ahead for that box)
#   -Check         list the visible message boxes of the PID (title, text, buttons); press nothing
# Exit: 0 pressed (prints whether the process then exited) or -Check listed; 1 no box / no OK
#   button / several boxes and no -Hwnd; 2 no such process; 3 refused (LabVIEW without -AllowLabVIEW).
# Never kills. Ported from H21_press_ok.ps1 (05 rule 99).
param(
    [Parameter(Mandatory = $true)][int]$ProcId,
    [long]$Hwnd = 0,
    [int]$WaitSeconds = 10,
    [switch]$AllowLabVIEW,
    [switch]$Check
)

$p = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
if (-not $p) { "STOP: no process $ProcId"; exit 2 }
"pid $ProcId name $($p.ProcessName)"
if ($p.ProcessName -ieq 'LabVIEW' -and -not $AllowLabVIEW) {
    "REFUSED: pid $ProcId is LabVIEW; its dialogs are the user's to answer (-AllowLabVIEW only with the user's go-ahead)"
    exit 3
}

Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public static class OkBox {
 public delegate bool P(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumWindows(P f, IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, P f, IntPtr l);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, int m, IntPtr w, IntPtr l);
 static string Cls(IntPtr h) { var c = new StringBuilder(256); GetClassName(h, c, 256); return c.ToString(); }
 public static string Txt(IntPtr h) { var t = new StringBuilder(1024); GetWindowText(h, t, 1024); return t.ToString(); }
 public static List<IntPtr> Boxes(uint want) { var r = new List<IntPtr>();
  EnumWindows((h, l) => { uint pid; GetWindowThreadProcessId(h, out pid);
   if (pid == want && IsWindowVisible(h) && Cls(h) == "#32770") r.Add(h); return true; }, IntPtr.Zero);
  return r; }
 public static List<string> Children(IntPtr box) { var r = new List<string>();
  EnumChildWindows(box, (h, l) => { r.Add(h.ToInt64() + "\t" + Cls(h) + "\t" + Txt(h)); return true; }, IntPtr.Zero);
  return r; } }
"@

$boxes = [OkBox]::Boxes([uint32]$ProcId)
"message boxes: $($boxes.Count)"
foreach ($b in $boxes) {
    "box hwnd $($b.ToInt64()) title [$([OkBox]::Txt($b))]"
    foreach ($c in [OkBox]::Children($b)) { "  $c" }
}
if ($Check) { 'check: nothing pressed'; exit 0 }
if ($boxes.Count -eq 0) { 'no message box'; exit 1 }

if ($Hwnd -ne 0) {
    $target = $boxes | Where-Object { $_.ToInt64() -eq $Hwnd }
    if (-not $target) { "STOP: hwnd $Hwnd is not a message box of pid $ProcId"; exit 1 }
} elseif ($boxes.Count -gt 1) {
    'STOP: several boxes; pass -Hwnd'; exit 1
} else { $target = $boxes[0] }

$ok = $null
foreach ($c in [OkBox]::Children($target)) {
    $f = $c.Split("`t")
    if ($f[1] -eq 'Button' -and ($f[2] -replace '&', '') -eq 'OK') { $ok = [IntPtr][long]$f[0]; break }
}
if (-not $ok) { 'STOP: no OK button in that box'; exit 1 }
"pressing OK (BM_CLICK) hwnd $($ok.ToInt64()) in box $($target.ToInt64())"
[void][OkBox]::PostMessage($ok, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)
$exited = $p.WaitForExit($WaitSeconds * 1000)
"pid $ProcId exited within $WaitSeconds s: $exited"
exit 0
