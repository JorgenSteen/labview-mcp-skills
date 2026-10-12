# =============================================================================
# lv_windows.ps1 - lists every top-level window of the LabVIEW process and flags
# unsaved VIs ("*" in a title) and possible dialogs, with no LabVIEW call: the
# guard before a LabVIEW restart (skill lv-restart, route a; 05 rule 96).
# =============================================================================
# Usage (PowerShell, read-only, never closes or kills anything):
#   powershell -NoProfile -ExecutionPolicy Bypass -File lv_windows.ps1 [-ProcessName LabVIEW] [-All] [-Check]
#   -All    also print hidden windows that have a title (the ignore list is applied to the flags only)
#   -Check  self-test of the title classifier on built-in sample titles; touches no process
# Output: time, LabVIEW PID(s) + StartTime, Nigel processes (NI.NigelLocalService = the gRPC
#   service; LVNigelChat = the chat window, which may end together with LabVIEW), the LVAutoSave
#   count (found from the shell's Documents folder, which may be redirected, e.g. to OneDrive),
#   one line per visible window "class | title | kind", then the verdict.
# Exit: 0 clean; 1 unsaved or possible dialog flagged; 2 no LabVIEW process or more than one.
# Limits (H19): a modified VI with no open window does not show; a running VI (e.g. a launcher)
#   is not detected; a VI panel with a custom title (Window Appearance) is flagged as a possible
#   dialog - check it by eye; panels opened in a project show "<vi> Front Panel on <proj>/My Computer".
param(
    [string]$ProcessName = 'LabVIEW',
    [switch]$All,
    [switch]$Check
)

# Hidden windows LabVIEW always has; never a dialog (H19).
$IgnoreHidden = @('Context Help', 'Tools', 'Set Title', 'RunService.vi', 'Closed', 'Window monitor')

function Get-WindowKind([string]$title, [bool]$visible) {
    if ($title -match '\*') { return 'UNSAVED' }
    if (-not $visible) {
        if ($title -eq '' -or $IgnoreHidden -contains $title) { return 'hidden-system' }
        return 'hidden-other'
    }
    if ($title -eq '' ) { return 'untitled' }
    if ($title -eq 'LabVIEW') { return 'labview-frame' }
    if ($title -match '^Getting Started') { return 'getting-started' }
    if ($title -match '\.lvproj - Project Explorer$') { return 'project' }
    if ($title -match '\.(vi|vim|vit|ctl|ctt)( (Front Panel|Block Diagram))?( on .+)?$') { return 'vi' }
    return 'POSSIBLE-DIALOG'
}

if ($Check) {
    $samples = @(
        @('PRJ-receiver.vi', $true, 'vi'),
        @('PRJ-launcher.vi Front Panel on Demo.lvproj/My Computer', $true, 'vi'),
        @('PRJ-launcher.vi Block Diagram on Demo.lvproj/My Computer', $true, 'vi'),
        @('Demo.lvproj - Project Explorer', $true, 'project'),
        @('LabVIEW', $true, 'labview-frame'),
        @('Getting Started', $true, 'getting-started'),
        @('*PRJ-ROOT-helper_loop.vi Block Diagram', $true, 'UNSAVED'),
        @('Save Changes', $true, 'POSSIBLE-DIALOG'),
        @('Receiver', $true, 'POSSIBLE-DIALOG'),
        @('Context Help', $false, 'hidden-system'),
        @('RunService.vi', $false, 'hidden-system'),
        @('Something else', $false, 'hidden-other')
    )
    $fail = 0
    foreach ($s in $samples) {
        $k = Get-WindowKind $s[0] $s[1]
        $ok = ($k -eq $s[2]); if (-not $ok) { $fail++ }
        '{0,-4} visible={1,-5} kind={2,-16} title=[{3}]' -f ($(if ($ok) { 'ok' } else { 'FAIL' })), $s[1], $k, $s[0]
    }
    "check: $($samples.Count - $fail)/$($samples.Count) ok"
    if ($fail) { exit 1 } else { exit 0 }
}

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class LvWin {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
}
"@

"time $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff')"
$lv = @(Get-Process $ProcessName -ErrorAction SilentlyContinue)
foreach ($p in $lv) { "$ProcessName PID $($p.Id) StartTime $($p.StartTime.ToString('yyyy-MM-dd HH:mm:ss.fff')) Path $($p.Path)" }
foreach ($n in 'NI.NigelLocalService', 'LVNigelChat') {
    $q = @(Get-Process $n -ErrorAction SilentlyContinue)
    foreach ($p in $q) { "$n PID $($p.Id) StartTime $($p.StartTime.ToString('yyyy-MM-dd HH:mm:ss'))" }
    if ($q.Count -eq 0) { "$n NOT RUNNING" }
}
$docs = [Environment]::GetFolderPath('MyDocuments')
$as = Join-Path $docs 'LabVIEW Data\LVAutoSave'
if (Test-Path -LiteralPath $as) { "LVAutoSave count $(@(Get-ChildItem -LiteralPath $as -Recurse -File -Force).Count) ($as)" }
else { "LVAutoSave missing ($as)" }

if ($lv.Count -ne 1) { "STOP: $ProcessName process count $($lv.Count) (0 = not running; >1 = ask which one)"; exit 2 }

$ids = @([uint32]$lv[0].Id)
$script:rows = New-Object System.Collections.ArrayList
$cb = [LvWin+EnumProc]{ param($h, $l)
    $procId = [uint32]0; [void][LvWin]::GetWindowThreadProcessId($h, [ref]$procId)
    if ($ids -contains $procId) {
        $t = New-Object System.Text.StringBuilder 512; [void][LvWin]::GetWindowText($h, $t, 512)
        $c = New-Object System.Text.StringBuilder 256; [void][LvWin]::GetClassName($h, $c, 256)
        $vis = [LvWin]::IsWindowVisible($h)
        [void]$script:rows.Add([pscustomobject]@{ Class = $c.ToString(); Title = $t.ToString(); Visible = $vis; Kind = (Get-WindowKind $t.ToString() $vis) })
    }
    return $true }
[void][LvWin]::EnumWindows($cb, [IntPtr]::Zero)

"top-level windows: $($script:rows.Count)"
foreach ($r in $script:rows) {
    if ($r.Visible -or ($All -and $r.Title -ne '') -or $r.Kind -eq 'UNSAVED') {
        'visible={0,-5} {1,-16} class={2} title=[{3}]' -f $r.Visible, $r.Kind, $r.Class, $r.Title
    }
}
$unsaved = @($script:rows | Where-Object { $_.Kind -eq 'UNSAVED' })
$dialogs = @($script:rows | Where-Object { $_.Kind -eq 'POSSIBLE-DIALOG' })
$other = @($script:rows | Where-Object { $_.Kind -eq 'hidden-other' })
"hidden titled windows not in the ignore list: $($other.Count) (informational; -All lists them)"
"verdict: unsaved $($unsaved.Count)  possible dialogs $($dialogs.Count)"
if ($unsaved.Count -or $dialogs.Count) { exit 1 } else { exit 0 }
