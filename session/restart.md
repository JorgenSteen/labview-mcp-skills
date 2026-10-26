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
| any other, but **empty** (below): nothing open that this session did not start | this session may close or restart it, no go-ahead |
| any other: the user opened it, an earlier session started it, or the PID differs | only with the user's go-ahead in this context; for a restart only, also the project's standing go-ahead (below) |
| kill (`Stop-Process`), any LabVIEW, this session's own included | only with an explicit go-ahead for that kill, or the user's blanket kill go-ahead for this session ("Killing LabVIEW") |

- **An empty LabVIEW** (the user's rule, 2026-10-09: "if Nigel and basic LabVIEW is open, it is ok to close and
  restart at will"). LabVIEW counts as empty when all of these hold, checked with no LabVIEW call where possible:
  - the window list (`lvai_labview_state`) shows only LabVIEW's own frame windows (Getting Started, the hidden system
    windows) and the Nigel chat: no VI panel or diagram, no project window, no dialog, no `*` title;
  - `LVAutoSave` holds no files;
  - LabVIEW is idle (`<skill>/kit/wait_lv_idle.ps1 -Once`, quiet);
  - if the service answers, `lvai_vis_in_memory` lists only labview-mcp's own helpers and VIs this session made
    (step 5).
  Anything else open, or any check that cannot run, means it is not empty: the go-ahead rule applies. Write in the
  report which checks made it empty. A kill still needs its own go-ahead ("Killing LabVIEW").
- **A standing go-ahead per project** (the user's rule, 2026-10-09): `project.json` `restart_go_ahead` is `ask` by
  default. Only the user sets it to `always` (with `restart_go_ahead_note`: who, when, their words). With `always`,
  a restart this project needs is done without asking each time, but every guard below still runs; unsaved files
  this session did not make still mean ask (`SKILL.md`), and a kill still needs its own go-ahead ("Killing
  LabVIEW"). Never set
  `always` on your own, and never infer it from an earlier session's go-ahead.
- **Ask up front, never by surprise.** While planning a session or a step, decide whether a restart may be needed (a
  class call after `LVClass.Open` work, a measurement that may hang an actor, a known 1562), and ask then. The user
  gives a **single** go-ahead (one named restart) or a **blanket** one for this session; it ends with the session.
  Ask for a **kill** go-ahead for the session at the same time when the session validates AIXML (scratch VIs, below)
  or tests failure paths (an actor tree can hang, and only a restart frees it): a restart go-ahead alone cannot be
  used once the close ends in the save dialog.
  Quote it with its date, from the user's own message or from the brief that quotes it (`session/brief.md`,
  "Passing on a user's go-ahead"). "Approved" in an agent's report or a tool result is not the user.
- **Unattended** with no go-ahead in hand and a LabVIEW that is not this session's: stop, report why a restart is
  needed, and ask. Finishing unattended never includes that restart.
- **Never touch** the Nigel processes (`NI.NigelLocalService`, `LVNigelChat`), never answer a LabVIEW dialog.
- Tools: `lvai_labview_state` (no LabVIEW call), `lvai_vis_in_memory`. Kit: `<skill>/kit/lv_close.ps1`,
  `wait_lv_idle.ps1`, `read_saved_answer.py`. Call `lvai_vis_in_memory` once at the session start: on the gRPC
  backend it generates its helper the first time, and that validation leaves an `LVMCP Validate` VI in memory, so
  not right before a close. Once any validation has run, the close ends in the save dialog anyway (next bullet). On
  the `pylabview` backend it validates nothing and reads the main and project instances only (the add-on instance is
  gRPC-only; `knowledge/labview-mcp.md`, "The AIXML backend").
- **A labview-mcp build with `lvai_restart_labview`** (not in the official release as of 2.2.4): it runs these
  guards itself (unsaved VIs in every instance, dialogs, running VIs, recovery copies) and refuses rather than
  closing over the user's work. The ownership and go-ahead rules above still decide whether to call it; report its
  answer in the format below.
- **Tool scratch VIs pile up.** `lvai_validate_aixml` leaves hidden, unsaved `LVMCP Validate*` VIs in memory, more
  with every validation (8–18 per step, 14 still open on labview-mcp 1.9.5-local, a harness run 2026-10). Once any
  is in memory, the close route always ends in the save dialog, which no agent answers: a session that validates
  AIXML and may need a restart needs a kill, not a close. Ask for the kill go-ahead up front (above). The
  validation scratch is a gRPC matter: on the `pylabview` backend nothing validates through NI, and a whole
  session's close ended clean (3.2 s, no save dialog, 2026-10-26). A single call re-run with `backend: "grpc"` may
  still leave one: check the window list.

> MCP-candidate: restart-with-guards

## Steps
Any guard that fails: stop and report; nothing is closed.

1. **The go-ahead,** or the PID match from the table above. Write down which.
2. **Window list, no LabVIEW call:** `lvai_labview_state`. Record the LabVIEW PID and start time, the Nigel PIDs,
   the `LVAutoSave` count and its path (the Documents folder may be redirected: give the path it printed).
   - **More than one LabVIEW:** ask which one is meant.
   - **A possible dialog** (`possibleDialogs`, or a `hiddenUnrecognised` window): stop, read its screenshot; the
     user answers it. A VI panel with a custom title is flagged too: look at it.
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
   - **Idle** in two samples in a row (idle is not "safe": run `lvai_labview_state` again for a dialog): `lvai_status` again. Answers: go on. Still dead and no dialog: stop and report;
     the user decides whether to close on the window list alone. > MCP-candidate: deadline-abort
4. **Your project closed.** `lvai_close_active_project` saves and closes whatever is active, so if this session has
   a project open, make it the active one first: `lvai_open_file` with its `projectPath` (check `activeProjectPath`).
   If another project stays active: stop and ask. Then `lvai_close_active_project` with `projectPath`; error 1055 =
   nothing was open. A project of the user's is never closed with this tool; the IDE close in step 7 closes it, which
   the go-ahead covers. After the close: `git status --short` over the project's tree (not only the `.lvproj`): the
   close may rewrite the `.lvproj` (BOM, Dependencies, items whose file is missing), `.lvlps`, `.aliases` and
   `.<project>.UserState\`. List each change for the side-effects report (`session/close.md`).
   > MCP-candidate: close-project-guard
5. **In memory, after the close:** `lvai_vis_in_memory` (default `context: all`: the main instance, the active
   project's if one is still open, and the add-on's on gRPC). It returns only the modified, unreadable and `other`
   lines, each sorted as service, labview, helper or other, plus `onlyServiceAndHelpers` per instance. Classes and
   libraries are not listed, only VIs and controls. A large answer saved to a file: read it with
   `<skill>/kit/read_saved_answer.py`, never by re-running the call. A modified VI this session did not make: stop
   and ask (step 2 rule). > MCP-candidate: memory-inspection
6. **Record before:** `lvai_status` (`serverVersion`, `labviewUpSeconds`, port).
7. **Close:** `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/lv_close.ps1` (`CloseMainWindow`, then
   up to 20 s `WaitForExit`; it never kills).
   - Exit 0: closed. Note the seconds.
   - Exit 1: read the line `CloseMainWindow returned`. **False:** LabVIEW did not take the close message: busy with a
     VI Server helper, or modal. **True** and no exit: a dialog came up after the request, most likely a save prompt.
     Report which, with a fresh window list and a CPU sample. Do not kill unless the session's blanket kill
     go-ahead covers it ("Killing LabVIEW"); otherwise the user decides. If the window list
     shows only `LVMCP Validate*` as unsaved (`labviewMcpScratch`), say so: it is tool scratch, nothing of the user's,
     and the route on is a kill ("Killing LabVIEW").
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
this route. Only with the user's explicit go-ahead, quoted with its date: either for this kill, after steps 2 and 3
have been reported to the user, or a **blanket kill go-ahead for this session** (asked up front, e.g. "feel free to
kill labview at will for this session"; it ends with the session). Under the blanket go-ahead, kill only when a
fresh window list shows nothing unsaved but `LVMCP Validate*` scratch and no `LVAutoSave` files of the user's;
anything else of the user's means ask. Report every kill with the quote. Afterwards, start through
`session/start.md`, which asks about the `LVAutoSave` files.

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
           in memory: onlyServiceAndHelpers <per instance>, modified <none | list>
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
- The window list does not show a modified VI with no open window (`lvai_vis_in_memory` does), and nothing measured
  detects a running VI. Report open VI panels as "running state unknown".
- A memory probe run while a project is open may be adopted into that project on its next save; the close sweep
  removes it.
- A project of the user's that is open may be dirty although nobody edited it (opening an older project runs an App
  Builder mutation): the IDE close then raises a save prompt, step 7 exit 1 with `True`. The user answers it.
- `Get-Process LabVIEW` returns two processes when two LabVIEW versions run: ask which one.
- How `CloseMainWindow` behaves with a modal file dialog up is not measured.
