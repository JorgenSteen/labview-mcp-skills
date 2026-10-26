# Start: make sure LabVIEW and the labview-mcp service answer

**When:** before the first LabVIEW call of a session, and whenever a LabVIEW call fails because nothing answers. The
router (`SKILL.md`) sends every task here first, so no other file in this skill deals with starting LabVIEW. They
all assume it is running. A subagent gets "LabVIEW is running (checked by the main session)" in its brief; if it
stops answering during the work, the agent stops and reports. It does not start or restart LabVIEW itself.

**Not here:** restarting a LabVIEW that runs but is hung or holds something in memory. That is `session/restart.md`,
with its guards and the user's go-ahead.

## Steps

0. **Which backend.** `pylv_status` (no LabVIEW needed): `aixmlBackend.serverDefault` is the route the tools take,
   `serverDefaultSource` why (usually the user's `settings.json`). Note it for the session's report and every brief;
   never change it (`knowledge/labview-mcp.md`, "The AIXML backend").
   - **`grpc`:** the steps below as written; `lvai_status` is the readiness check.
   - **`pylabview`:** LabVIEW is ready when it answers over ActiveX, and NI's gRPC service does not matter for the
     start. Step 1 is then `lvai_labview_state`: with one LabVIEW running and nothing flagged, `lvai_ensure_labview`
     (it starts nothing when one runs) must answer `"state": "ready"`, and you are done. With none running, go on at
     step 3. A failing `lvai_status` is no reason to open Nigel; only a call that must fall back to `grpc` needs the
     service, and it usually comes up with LabVIEW by itself.
1. **`lvai_status`.** If it answers, note the port and `labviewUpSeconds` for the session's report, then look at the
   IDE once with `lvai_labview_state` (no LabVIEW call; it reads Windows). Unsaved windows (`unsaved`, `*` in the
   title), `LVAutoSave` files or an open project that this session did not make mean the user is working (they may
   open the project between steps): note them, and ask before any close, save, restart or kill that would touch them
   (`SKILL.md`, "Save what you made; ask about the rest"). Then you are done.
2. **It does not answer: look at the processes** with `lvai_labview_state`. It answers while the service is blocked,
   and lists the LabVIEW processes (and whether this server started one), the Nigel processes
   (`NI.NigelLocalService`, `LVNigelChat`), the `LVAutoSave` count, every LabVIEW window sorted into kinds, and one CPU
   sample. Each possible dialog comes with a `screenshot` PNG: read it, the picture is the only way to tell which
   dialog it is.

   | What it shows | Do |
   |---|---|
   | no LabVIEW process | step 3 |
   | one LabVIEW, `possibleDialogs` not empty | Stop. A modal dialog blocks the service. Report the title and what the screenshot shows. The user answers it; never press a LabVIEW dialog yourself. |
   | one LabVIEW, `hiddenUnrecognised` not empty | Look at each one before going on: LabVIEW dialogs have reported themselves hidden (labview-mcp measured it). |
   | one LabVIEW, nothing flagged | step 4 (the service is not up yet) |
   | more than one LabVIEW process | Stop and ask the user which one is meant. |

3. **Start LabVIEW.**
   - **Check `LVAutoSave` first.** `lvai_ensure_labview` deletes those files by default. That is right for leftover
     recovery data, which would otherwise raise a modal recovery dialog that blocks the service. But after a crash
     they may be the user's unsaved work. If the count is above 0, ask the user before starting: recover by hand
     first, or let the start clear them. Never pass `keepAutoSave: true` on your own; the recovery dialog would
     block every call.
   - **Which LabVIEW:** `lvai_list_labview_installations` shows which one would be started (the newest, preferring
     32-bit, which hosts the AI service). If it is not the one the project needs, ask.
   - **`lvai_ensure_labview`.** It verifies that the launched process survives (`launchMethod`; none surviving is
     `launch-did-not-survive`, never a hopeful "starting"). While LabVIEW is still coming up, calling it once more is
     right: the second call finds the instance and waits.
4. **Wait for the service** (`grpc` only; on `pylabview` the start ended with `lvai_ensure_labview`'s `ready`, step 0,
   and this step is skipped). Call `lvai_status`. If it answers, you are done. The service comes up with LabVIEW
   itself, about 45 s after a cold start, with no Nigel chat opened (labview-mcp measured it 2026-10-17, with
   `NI.NigelLocalService` running; this skill said earlier that it starts with Nigel, which is refuted).
   If LabVIEW is visibly running (step 2 shows it) but `lvai_status` still fails after about two minutes, the service
   is not up (once seen: 30 listener ports, none serving). Then open the Nigel chat, the fallback that has brought it
   up: `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/lv_start_nigel_chat.ps1 -Version <ver> -Bitness <x86|x64> -Check`,
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

`LabVIEW: <already running (the user's) | started by this session (<s> s, launchMethod <m>, PID <pid>)> port <p | n/a>, up <s> s;
backend <grpc | pylabview> (<source>); Nigel chat: <running | opened | not needed>; LVAutoSave: <n> files <kept | cleared with the user's ok>`

Who started LabVIEW decides who may close it (`SKILL.md`, "The user's LabVIEW is the user's"). Keep the PID: a
LabVIEW with another PID later is not the one this session started.

Starting LabVIEW, opening the Nigel chat and clearing `LVAutoSave` are side effects. They go into the end-of-session
report (`session/close.md`).

> MCP-candidate: ensure-labview-complete. `lvai_labview_state` now tells "not running" and "blocked by a dialog"
> apart; still open: `lvai_ensure_labview` should warn before it deletes `LVAutoSave` files (a count, a dry run).
