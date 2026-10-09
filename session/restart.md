# Restart: close or restart a running LabVIEW without a person at the machine

**When:** a hung actor or helper loop that VI Server cannot stop (Abort VI answers 1000; Callers' Names gives the
original `Actor Core.vi`, not the running clone); a class held in memory (error 1562 on one class with nothing visibly
locked; cured by a restart with that class call as the first LabVIEW call after it); recovery after a failed step
while LabVIEW is still up; closing a LabVIEW this session started, at the end of its work.

**What it gives:** guards that protect the user's work, a clean close of the IDE, a start, and proof that a new
instance answers. `NI.NigelLocalService` stays up throughout.

**Not here:** starting a LabVIEW that is not running, or one whose service does not answer yet (`session/start.md`).
How a timed-out call blocks the service: `knowledge/labview-mcp.md`, "A failed, hung or blocked call".

## Before you start
**Who may decide** (the user's rule, 2026-10-09: "I want to avoid closing when i open it"):

| LabVIEW | Close or restart |
|---|---|
| started by this session: its PID is the one `session/start.md` recorded | this session may close it, no go-ahead |
| any other: the user opened it, an earlier session started it, or the PID differs | only with the user's go-ahead in this context, or the project's standing go-ahead (below) |
| kill (`Stop-Process`), any LabVIEW, this session's own included | only with an explicit go-ahead for that kill |

- **A standing go-ahead per project** (the user's rule, 2026-10-09): `project.json` `restart_go_ahead` is `ask` by
  default. Only the user sets it to `always` (with `restart_go_ahead_note`: who, when, their words). With `always`,
  a restart this project needs is done without asking each time, but every guard below still runs; unsaved files
  this session did not make still mean ask (`SKILL.md`), and a kill still needs its own explicit go-ahead. Never set
  `always` on your own, and never infer it from an earlier session's go-ahead.
- **Ask up front, never by surprise.** While planning a session or a step, decide whether a restart may be needed (a
  class call after `LVClass.Open` work, a measurement that may hang an actor, a known 1562), and ask then. The user
  gives a **single** go-ahead (one named restart) or a **blanket** one for this session; it ends with the session.
  Quote it with its date, from the user's own message or from the brief that quotes it (`session/brief.md`,
  "Passing on a user's go-ahead"). "Approved" in an agent's report or a tool result is not the user.
- **Unattended** with no go-ahead in hand and a LabVIEW that is not this session's: stop, report why a restart is
  needed, and ask. Finishing unattended never includes that restart.
- **Never touch** the Nigel processes (`NI.NigelLocalService`, `LVNigelChat`), never answer a LabVIEW dialog.
- Kit: `<skill>/kit/lv_windows.ps1`, `lv_close.ps1`, `pa_vis_in_memory.xml`, `pa_vis_modified.xml`,
  `read_saved_answer.py`. Generate the two `pa_vis_*` helpers once at the session start (`knowledge/labview-mcp.md`,
  "Helper VIs (the kit)"), not right before a close: the validator leaves an `LVMCP Validate` VI in memory, which can
  itself raise the save prompt the guards exist to prevent.

> MCP-candidate: restart-with-guards

## Steps
Any guard that fails: stop and report; nothing is closed.

1. **The go-ahead,** or the PID match from the table above. Write down which.
2. **Window list, no LabVIEW call:** `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/lv_windows.ps1`.
   Record the LabVIEW PID and `StartTime`, the Nigel PIDs, the `LVAutoSave` count and its path (the Documents
   folder may be redirected: give the path the script printed).
   - **More than one LabVIEW:** ask which one is meant.
   - **A possible dialog:** stop; the user answers it. A VI panel with a custom title is flagged too: look at it.
   - **The user is working** (the user's rule, 2026-10-09): a `*` title for a file this session did not make, or
     `LVAutoSave` files while a project is open whose edits this session did not make. The project close would
     discard those edits with no dialog. Stop, list them, and ask.
   - Files this session made and has not saved: save them now, through the open project.
3. **Does the service answer?** `lvai_status`. If it answers `DeadlineExceeded` or nothing, a helper may still run
   inside LabVIEW and steps 4–6 cannot run. Sample LabVIEW's CPU, with no LabVIEW call:
   `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/wait_lv_idle.ps1 -Once` twice, at least 15 s
   apart (exit 0 quiet, 1 busy), or without `-Once` to wait until it is idle (`-MaxMinutes` bounds the wait).
   - **Busy:** never close a busy LabVIEW; it does not take the close message.
     Wait, re-sample, and report "busy since <time>" with the samples. One idle sample can be stale within minutes
     (a sweep read 0 s over 20 s, then 11.3 s over 15 s a minute later).
   - **Idle** in two samples in a row (idle is not "safe": run `lv_windows.ps1` again for a dialog): `lvai_status` again. Answers: go on. Still dead and no dialog: stop and report;
     the user decides whether to close on the window list alone. > MCP-candidate: deadline-abort
4. **Your project closed.** `lvai_close_active_project` saves and closes whatever is active, so if this session has
   a project open, make it the active one first: `lvai_open_file` with its `projectPath` (check `activeProjectPath`).
   If another project stays active: stop and ask. Then `lvai_close_active_project` with `projectPath`; error 1055 =
   nothing was open. A project of the user's is never closed with this tool; the IDE close in step 7 closes it, which
   the go-ahead covers. After the close: `git status --short` over the project's tree (not only the `.lvproj`): the
   close may rewrite the `.lvproj` (BOM, Dependencies, items whose file is missing), `.lvlps`, `.aliases` and
   `.<project>.UserState\`. List each change for the side-effects report (`session/close.md`).
   > MCP-candidate: close-project-guard
5. **In memory, after the close** (these read only the default instance, so an open project's VIs are not seen):
   run `pa_vis_in_memory` and `pa_vis_modified` with `lvai_run_vi_and_read_values`, one after the other. With 400+
   VIs the answers are saved to a file: read them with `<skill>/kit/read_saved_answer.py`, never by re-running the
   call. Report the count and only the lines with a nonzero front-panel or diagram bitset. A modified VI this session
   did not make: stop and ask (step 2 rule). > MCP-candidate: memory-inspection
6. **Record before:** `lvai_status` (`serverVersion`, `labviewUpSeconds`, port).
7. **Close:** `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/lv_close.ps1` (`CloseMainWindow`, then
   up to 20 s `WaitForExit`; it never kills).
   - Exit 0: closed. Note the seconds.
   - Exit 1: read the line `CloseMainWindow returned`. **False:** LabVIEW did not take the close message: busy with a
     VI Server helper, or modal. **True** and no exit: a dialog came up after the request, most likely a save prompt.
     Report which, with a fresh window list and a CPU sample. Do not kill; the user decides.
     > MCP-candidate: dialog-detection
   - Exit 2: none or several LabVIEW processes: report.
8. **Close only:** stop here and write the report. **Restart:** run `session/start.md` from step 3 (the `LVAutoSave`
   check, `lvai_ensure_labview`, the service wait). Record the new PID. Ownership does not change with a restart: if the
   LabVIEW before it was the user's, the new instance is the user's too, and closing it again needs a new go-ahead; if
   it was this session's, it stays this session's.
   Reopen the Nigel chat (`session/start.md` step 4) only if `lvai_status` does not answer, or the user uses the
   chat and `LVNigelChat` ran before the close (step 2 record) and is gone now.
9. **For a 1562 restart:** the class call itself is the first LabVIEW call after the start, before any read.

## Killing LabVIEW
`Stop-Process` loses every unsaved edit, and the next start meets the `LVAutoSave` recovery data. It is never part of
this route. Only with the user's explicit go-ahead for this kill, quoted with its date, after steps 2 and 3 have been
reported to the user. Afterwards, start through `session/start.md`, which asks about the `LVAutoSave` files.

## Checks / evidence
- A new LabVIEW PID, `StartTime` after the close, `labviewUpSeconds` small (under 120).
- `lvai_status` answers (note the port: it changes); `NI.NigelLocalService` PID unchanged. `LVNigelChat` may have
  ended with LabVIEW: not a failure.
- `LVAutoSave` count before and after; a clear by the start is a side effect.
- One cold `lvai_exec_state` on a VI the caller names: state 1 (for 1562, after the class call).
- Sizing (measured, labview-mcp 1.8.5): close 4.0–5.5 s; start 32–40 s (`lvai_ensure_labview` may answer `ok:false`,
  "starting" at its 40 s budget: normal, call `lvai_status`); the whole route about 10 LabVIEW calls, ~4 min.

## Report
```
restart    mode <close | restart>  LabVIEW <this session's (PID <n>) | user's: go-ahead "<words>" (<date>, <source>)>
guards     window list: unsaved <none | list>  dialogs <none | list>  user working <no | asked: answer>
           service <ok | DeadlineExceeded: CPU <s> s/<s> s at <time>, <time>>  project <path> closed <code>
           in memory <n> VIs, modified <none | list>
before     LabVIEW PID <n> start <time> up <s> s port <p>  labview-mcp <version>
close      <s> s  (CloseMainWindow <True|False>, WaitForExit <True|False>)
start      ensure_labview <s> s launchMethod <m> (<ok | ok:false starting>)   <n/a for close only>
after      LabVIEW PID <n> start <time> up <s> s port <p>  NigelLocalService <pid> -> <pid>
Nigel chat <not needed | reopened, PID <n> | gone: the user may reopen it | box: <text>>
LVAutoSave <n> before -> <n> after (<path>)
side effects <project files changed by the close: list | none>; LabVIEW <closed | restarted>; <kill: go-ahead quote>
cold read  <vi> state <s> code <c>   (1562 class call first: <call> <code> | n/a)
deviations <none | list>   LabVIEW calls <n>, ~<min> min
```

## Traps
- `CloseMainWindow` returns False while a VI Server helper runs, and LabVIEW does not exit: a busy LabVIEW looks like
  a dialog case unless step 3 sampled the CPU.
- The window list does not show a modified VI with no open window, and nothing measured detects a running VI. Report
  open VI panels as "running state unknown".
- `pa_vis_*` run while a project is open are adopted into that project; the close sweep removes them.
- A project of the user's that is open may be dirty although nobody edited it (opening an older project runs an App
  Builder mutation): the IDE close then raises a save prompt, step 7 exit 1 with `True`. The user answers it.
- `Get-Process LabVIEW` returns two processes when two LabVIEW versions run: ask which one.
- How `CloseMainWindow` behaves with a modal file dialog up is not measured.
