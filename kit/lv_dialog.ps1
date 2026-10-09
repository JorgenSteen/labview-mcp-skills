# =============================================================================
# lv_dialog.ps1 - lists LabVIEW's visible windows and the buttons and text of the
# dialog whose title matches -Match, with no LabVIEW call: names the modal dialog
# (e.g. "Find the VI Named ...") that blocks the labview-mcp service, for the report.
# =============================================================================
# Usage (PowerShell; read-only unless -Escape):
#   powershell -NoProfile -ExecutionPolicy Bypass -File lv_dialog.ps1
#       [-Match 'Find the VI'] [-ProcessName LabVIEW] [-Escape] [-Check]
#   Default: prints every visible top-level window of the one LabVIEW process (handle, class,
#   title) and, for each window whose title contains -Match, its child controls (buttons, text).
#   Nothing is pressed or closed.
#   -Escape  CANCELS the one matching dialog: brings it to the front and sends the Esc key.
#            A LabVIEW dialog is the user's to answer (SKILL.md, safety rules). Use -Escape ONLY
#            with the user's explicit go-ahead in this context, for this dialog. It refuses when
#            several windows match, and when the dialog cannot be brought to the front (the key
#            would go to another window).
#   -Check   with -Escape: say which window would get the Esc key, and send nothing.
# Exit: 0 a matching window was found (listed; with -Escape: it closed); 1 no window matches;
#   2 no LabVIEW process or more than one; 3 -Escape refused (several matches, or not in front);
#   4 Esc sent but the window is still visible (stop; the user answers it).
# Provenance: ported from the skills audit's scratch dialog script (run L3, a JKI JSON
#   "Find the VI" dialog that held a bind call for 720 s, cancelled with the user's go-ahead).
param(
    [string]$Match = 'Find the VI',
    [string]$ProcessName = 'LabVIEW',
    [switch]$Escape,
    [switch]$Check
)

Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public static class LvDlg {
 public delegate bool P(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumWindows(P f, IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, P f, IntPtr l);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 public static string Cls(IntPtr h) { var c = new StringBuilder(256); GetClassName(h, c, 256); return c.ToString(); }
 public static string Txt(IntPtr h) { var t = new StringBuilder(1024); GetWindowText(h, t, 1024); return t.ToString(); }
 public static List<IntPtr> Top(uint want) { var r = new List<IntPtr>();
  EnumWindows((h, l) => { uint pid; GetWindowThreadProcessId(h, out pid); if (pid == want && IsWindowVisible(h)) r.Add(h); return true; }, IntPtr.Zero); return r; }
 public static List<string> Kids(IntPtr p) { var r = new List<string>();
  EnumChildWindows(p, (h, l) => { r.Add("  child " + h.ToInt64() + " " + Cls(h) + " [" + Txt(h) + "]"); return true; }, IntPtr.Zero); return r; } }
"@

$lv = @(Get-Process $ProcessName -ErrorAction SilentlyContinue)
if ($lv.Count -ne 1) { "STOP: $ProcessName process count $($lv.Count) (0 = not running; >1 = ask which one)"; exit 2 }
$p = $lv[0]
"$ProcessName PID $($p.Id)"
$hits = New-Object System.Collections.ArrayList
foreach ($h in [LvDlg]::Top([uint32]$p.Id)) {
    $t = [LvDlg]::Txt($h)
    "window $($h.ToInt64()) class $([LvDlg]::Cls($h)) [$t]"
    if ($Match -and $t -like "*$Match*") { [void]$hits.Add($h); [LvDlg]::Kids($h) }
}
if ($hits.Count -eq 0) { "no visible window matching '$Match'"; exit 1 }
"matching windows: $($hits.Count)"
if (-not $Escape) { exit 0 }

if ($hits.Count -gt 1) { "REFUSED: $($hits.Count) windows match '$Match'; narrow -Match"; exit 3 }
$hit = $hits[0]
if ($Check) { "check: would bring window $($hit.ToInt64()) [$([LvDlg]::Txt($hit))] to the front and send Esc; sent nothing"; exit 0 }
[void][LvDlg]::SetForegroundWindow($hit); Start-Sleep -Milliseconds 400
if ([LvDlg]::GetForegroundWindow() -ne $hit) { "REFUSED: the dialog is not in front; Esc not sent (the user answers it)"; exit 3 }
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('{ESC}'); Start-Sleep -Seconds 2
$still = [LvDlg]::IsWindowVisible($hit)
"sent Esc; window still visible: $still"
if ($still) { exit 4 } else { exit 0 }
