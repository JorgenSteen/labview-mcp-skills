# Start: make sure LabVIEW and the labview-mcp service answer

**When:** before the first LabVIEW call of a session, and whenever a LabVIEW call fails because nothing answers. The
router (`SKILL.md`) sends every task here first, so no other file in this skill deals with starting LabVIEW. They
all assume it is running. A subagent gets "LabVIEW is running (checked by the main session)" in its brief; if it
stops answering during the work, the agent stops and reports. It does not start or restart LabVIEW itself.

**Not here:** restarting a LabVIEW that runs but is hung or holds something in memory. That is `session/restart.md`,
with its guards and the user's go-ahead.

## Steps

1. **`lvai_status`.** If it answers, you are done. Note the port and `labviewUpSeconds` for the session's report.
2. **It does not answer: look at the processes,** with no LabVIEW call:
   `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/lv_windows.ps1`. It lists the LabVIEW process,
   the Nigel processes (`NI.NigelLocalService`, `LVNigelChat`), the `LVAutoSave` count, and every LabVIEW window
   (unsaved VIs and possible dialogs flagged).

   | What it shows | Do |
   |---|---|
   | no LabVIEW process (exit 2, none listed) | step 3 |
   | one LabVIEW, a possible dialog flagged | Stop. A modal dialog blocks the service. Report the window title. The user answers it; never press a LabVIEW dialog yourself. |
   | one LabVIEW, nothing flagged | step 4 (the service is not up yet, or Nigel is not open) |
   | more than one LabVIEW process | Stop and ask the user which one is meant. |

3. **Start LabVIEW.**
   - **Check `LVAutoSave` first.** `lvai_ensure_labview` deletes those files by default. That is right for leftover
     recovery data, which would otherwise raise a modal recovery dialog that blocks the service. But after a crash
     they may be the user's unsaved work. If the count is above 0, ask the user before starting: recover by hand
     first, or let the start clear them. Never pass `keepAutoSave: true` on your own; the recovery dialog would
     block every call.
   - **Which LabVIEW:** `lvai_list_labview_installations` shows which one would be started (the newest, preferring
     32-bit, which hosts the AI service). If it is not the one the project needs, ask.
   - **`lvai_ensure_labview`.** A cold start takes about 36–40 s. It may answer `ok: false`, state "starting", at the
     end of its budget. That is normal: go to step 4, and do not call it again at once.
4. **Wait for the service.** Call `lvai_status`. If it answers, you are done.
   If LabVIEW is visibly running (step 2 shows it) but `lvai_status` keeps failing, the AI gRPC service is not up.
   It starts with Nigel, not with the IDE. Open the Nigel chat without a person:
   `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/lv_start_nigel_chat.ps1 -Version <ver> -Bitness <x86|x64> -Check`,
   then the same without `-Check`.
   - **`-Version`** is the add-on folder's name under `<Program Files>\NI\LVAddons\lvai\`, e.g. `26.3` for 2026 Q3.
   - **`-Bitness`** is `x86` when LabVIEW.exe is under `Program Files (x86)`, otherwise `x64`.
   - **Exit 0:** the chat window is up. Call `lvai_status` once more.
   - **Exit 1:** the chat exited or shows a message box. Stop and report the box text. Only a box that this start
     raised may be closed, with `<skill>/kit/lv_press_ok.ps1 -ProcId <chat pid>`.
   Never start `LVNigelChat.exe` any other way. Without both `--lv-version` and `--lv-bitness` it never exits and
   leaves a modal error box.
5. **Still no answer:** stop and report what steps 2–4 showed. Do not loop on `lvai_ensure_labview`.

## Report (one line per session)

`LabVIEW: <already running (the user's) | started by this session (<s> s, launchMethod <m>, PID <pid>)> port <p>, up <s> s;
Nigel chat: <running | opened | not needed>; LVAutoSave: <n> files <kept | cleared with the user's ok>`

Who started LabVIEW decides who may close it (`SKILL.md`, "The user's LabVIEW is the user's"). Keep the PID: a
LabVIEW with another PID later is not the one this session started.

Starting LabVIEW, opening the Nigel chat and clearing `LVAutoSave` are side effects. They go into the end-of-session
report (`session/close.md`).

> MCP-candidate: `lvai_status` should say plainly whether LabVIEW is not running, running without the service, or
> blocked by a dialog. `lvai_ensure_labview` should open Nigel itself and warn before it deletes `LVAutoSave` files.
> See `MCP-CANDIDATES.md#ensure-labview-complete`.
