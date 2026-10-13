# labview-mcp: operating rules, known gaps, quirks

The toolchain layer: how to drive labview-mcp without hurting the files or the service, what each tool gets wrong,
and the LabVIEW scripting quirks met on the way. Measured with labview-mcp 1.7.2 to 1.9.5 on LabVIEW 2026 Q3 32-bit;
each gap carries its version in brackets. On a newer labview-mcp, re-check a gap before working around it.

`> MCP-candidate: <id>` marks a workaround for a gap that `MCP-CANDIDATES.md` proposes to fix in labview-mcp. Kit files
are `<skill>/kit/<file>`. Step-by-step routes are in `ops/` and `session/`; this file holds the rules they share. How
AF behaves is in `knowledge/actor-framework.md`. What labview-mcp documents itself (its `CLAUDE.md`, its `docs/`) is
not repeated here.

## Operating rules

### One LabVIEW, one caller
- **Strictly sequential LabVIEW calls:** one `lvai_*`/`pylv_*` call at a time, never in parallel, not even reads or
  the after-checks of a run. LabVIEW serialises the work anyway (labview-mcp measured six calls sent together at
  559 ms against 543 ms in sequence), so parallel calls gain nothing and let one slow call block the rest. Agents
  broke this rule in four pilot sessions although their brief said it: say it plainly. > MCP-candidate: call-lock
- One LabVIEW agent at a time; the main session makes no LabVIEW call while it runs. Docs-only agents may run beside
  it. A project is global to the LabVIEW instance: an agent that opens, closes or swaps changes it for every caller.

### A failed, hung or blocked call: stop and report
- **`DeadlineExceeded` does not stop the work.** The VI Server helper keeps running inside LabVIEW, and every later
  call answers `DeadlineExceeded`, `lvai_status` included, until it ends (a cold sweep ran ~2.5 h past its 300 s
  deadline). Make no further LabVIEW call and do not retry with a larger budget: that starts the load again. Check
  without LabVIEW: `<skill>/kit/lv_windows.ps1` (dialogs, `*` titles) and LabVIEW's CPU time sampled twice at least
  15 s apart (one idle sample can be stale within minutes). Report "busy since <time>". [1.8.5] (audit rule
  candidate 104) > MCP-candidate: deadline-abort
- **A modal dialog blocks the whole gRPC service** until a person answers it; the call only times out. Sources met: a
  missing dependency (`Find the VI Named "<qualified name>"`, which held a bind for 720 s), a library item whose file
  is missing (a search dialog on load), leftover `LVAutoSave` data (a recovery offer at start), unsaved VIs at a close
  (a save prompt). The agent never answers a dialog; the user does. [1.8.5] (pilot rule 12; audit rule candidate 103)
  > MCP-candidate: dialog-detection
- A crash, a hang or a dialog ends the agent's LabVIEW work. Report LabVIEW's state (open project, unsaved VIs, which
  dialog) and what was not verified. No retry loops.
- Before loading code this session did not build, check offline that its dependencies resolve: every hang in the
  audit came from loading code with missing packages (proposal X-1, open in the audit).
  > MCP-candidate: offline-loadability
- Close, restart or kill LabVIEW only as `SKILL.md`, "The user's LabVIEW is the user's", allows (this session's own
  or an empty LabVIEW; the user's go-ahead in this context; the project's standing restart go-ahead; a kill only with
  its own or the session's kill go-ahead). The routes and checks are in `session/restart.md`. Never close a LabVIEW
  with the user's work open without asking.

### Project open or closed, per kind of call

| Call or step | Project |
|---|---|
| `lvai_exec_state` and the sweep helper (open: good VIs read state 0); Clean Up Diagram; re-save; class/library icon helpers (open: 1562) | **closed** |
| front-panel property setters and cold read-backs, VI description edit (`pa_replace_description`, `pa_set_vi_descriptions`), `pa_set_plot_names`, `pa_wire_by_label`; `pylv_extract`/`pylv_rebuild` with kit bundle scripts; `lvai_generate_vi_with_events`; `lvai_set_event_data_fields` | **closed** |
| byte-exact kit edits of `.lvclass`/`.lvlib`/`.lvproj`; file deletes; any git restore, checkout, revert or reset | **closed** |
| AF override and hook helpers, `pa_save_member`, `pa_clean_member`, `pa_rename_member`; `lvai_swap_subvis` (`Replace` is a silent no-op outside the IDE's own instance) | **open and active** |
| `lvai_wire_dynamic_events`, `pa_wire_dyn_right`, `pa_wire_dyn_deep`, `pa_set_panel_on_call`, `pa_switch_and_reset_boolean`, `pa_array_element_replace`; `lvai_add_class_field`, `lvai_bind_class_fields`, `lvai_add_class_method` on an existing member, `lvpdc_export`/`lvpdc_import` | **open and active** |
| `pa_set_class_description`, `pa_class_folder_add_files`, `pa_class_folder_create_and_move`, `pa_class_folder_move`, `pa_save_libraries`, `pa_project_vis_modified` | **open and active** |
| `pa_insert_series_branch`, `pa_remove_series_block`, `pa_wire_nodes`, `pa_reg_to_control`, `pa_reg_indicator`, `pa_replace_constant_deep`, `pa_save_orphan` | **open and active** |
| `lvai_create_accessors` | **open and active** (`projectPath` is the project to tidy; the tool's own text requires an active project; it opened a closed one anyway in an evaluation, 2026-10) |
| `lvai_create_typedef` | closed with no `projectPath` (stays closed), or `projectPath` = the active project |
| converting a VI that calls library or class members | open, one member opened through it |
| test VIs and behaviour runs | as `checks.json` says; closed by default |

Wrong-state codes: 1055 (nothing open or active), 1073 (class held elsewhere), 1562 (project or library locked). VI
Server reads of what is in memory (`All VIs In Memory`, `Modifications:` bitsets, `Execution:State`) see only the
**default application instance**: an open project's VIs are not listed, and classes and libraries never are. A probe
VI run while a project is open is adopted into that project. > MCP-candidate: project-state-guard

### Opening and closing a project
- **`lvai_close_active_project` saves and closes whatever project is active.** `projectPath` does not choose the
  project; it names the file swept afterwards, and the tool does not compare it with the active one. Without it the
  tool reads the active path itself (a pilot close saved and closed an unrelated, non-git project of the user's). So
  make sure yours is the active one before the close: `lvai_open_file` with your `projectPath` makes it active and
  answers `projectBecameActive` and `activeProjectPath` (an open of a second project switches the active one); the
  window list shows which project windows are open. If another project would be closed, stop and report. Pass
  `projectPath` anyway. Error 1055 = nothing was open: fine. [1.8.5; tool source v1.8.0 and v1.8.5] (pilot rule 95)
  > MCP-candidate: close-project-guard
- **What opening and closing write** [1.8.5]: the open rewrites `.aliases` (the `My Computer` IP becomes this PC's)
  and, on a project with older App Builder specs, runs a build-spec mutation that leaves the project dirty. The close
  saves, then LabVIEW rebuilds the `.lvproj`: Dependencies regenerated from what resolves (461 lines dropped when
  packages were missing), `NI.LV.All.SaveVersion` added, the UTF-8 BOM dropped or added, `.lvlps` rewritten,
  `.<project>.UserState\` created. The tool's sweep then removes items it adopted (helper VIs, `user.lib\LV_MCP`
  sockets) and **every item whose file is missing** (on a foreign project: a user's item). Acceptable in a git repo:
  commit before, list every such change in the end report (`session/close.md`). Without git: `dot-labview.md`,
  "No git". (audit rule candidates 101, 102, 107; pilot rules 34, 83) > MCP-candidate: close-project-guard
- **A large project opens slowly:** ~550 items passed the 120 s default and answered `DeadlineExceeded` while the open
  went on. Pass `timeoutSeconds` 300 or more, then check the window list for a dialog. [1.8.5]
  > MCP-candidate: project-open-report
- **`LVAutoSave` files while a project is open mean unsaved edits in memory**; the tool's close discards them with no
  dialog (18 files to 0). If this session did not make those edits, the user is probably working in LabVIEW: ask
  before the close (`SKILL.md`, "Save what you made; ask about the rest"). [1.8.5] (audit rule candidate 111)
- **The close discards an unsaved member edit:** a member VI left dirty by a failed in-place edit (nothing saved) was
  not saved by `lvai_close_active_project`; the file stayed unchanged. After a failed, unsaved edit, closing the
  project is a clean undo. (evaluation 2026-10)
- Calls that close and save the active project as a side effect: `lvai_create_typedef` with another project's
  `projectPath`, `lvai_generate_vi` with `panePattern`, `lvai_wire_dynamic_events` with its default `finishUserEvents`.
  [1.8.0–1.8.5] (pilot rules 54, 67)
- `lvai_open_file` relinks callers only with the project pair (`projectPath` + `projectName`); a loose open lands in
  another application instance. It gives no per-VI result for `viPath`. [1.8.5] (pilot rule 87)

### Helper VIs (the kit)
- Generate kit helpers (`<skill>/kit/*.xml`) with `lvai_generate_vi` (`measurePane: false`) into the project's
  proof folder when `project.json` names one (`proof_folder`), otherwise `%TEMP%\LabVIEWMCP\helpers\<name>.vi`
  (the user's rule, 2026-10-13). Generate while NO project is active: a helper generated or exported while a project
  is active is adopted into it (a foreign project's window turned `*` in an evaluation, 2026-10), and survives the
  close sweep. A cached
  helper is current when its answer carries every output its `.xml` names; otherwise regenerate it and run again (no
  LabVIEW call just to check). (pilot rule 11)
- Run helpers with `lvai_run_vi_and_read_values`, `inputsJson` = the control labels. **Absolute, long-form paths**
  only: no `%TEMP%`, no 8.3 short names (`C:\Users\ABCDEF~1.XYZ\...`). **Omit an input rather than pass `""`**: the
  runner refuses an empty value. The runner's own rule, for a control labelled exactly `project path`: omitted = the
  default instance (project closed); any text = the active project's instance. Give a helper's own input for a
  project file another label (an evaluation, 2026-10, used `new lvproj path`). (pilot rule 47)
- The runner cannot set arrays: a list input is one `;`-separated string. From ~100 paths the string and its answer
  pass the size limit: use the `*_file` twins with a list file (`sweep_paths.py --out`). The icon apply helper splits
  with Spreadsheet String To Array, so a trailing `;` there is an empty path (error 7); the loop helpers accept it.
  (pilot rules 58, 59) > MCP-candidate: runner-array-inputs
- **Save in a separate call** after a scripted edit (`pa_save_member`): one in-run save wrote a file without its `LIvi`
  link block (cause not proven; the extra save is cheap). Save a half-edited VI before a project close, so the close
  raises no save prompt. Every error indicator of a helper must read 0. (pilot rules 79, 90)
- A tool answer too large to return is saved to a file: read it with `<skill>/kit/read_saved_answer.py`, never by
  re-running the call. (pilot rule 33) > MCP-candidate: read-named-indicators

### LabVIEW files are never edited by hand
- No `sed -i`, heredoc or text edit on `.vi`, `.ctl`, `.lvclass`, `.lvlib`, `.lvproj` (Git Bash turns CRLF into LF).
  Use the kit's byte-exact scripts (`set_scope.py`, `remove_members.py`, `lvproj_drop.py`, `lvproj_move.py`,
  `lvproj_add_toplevel.py`, `repair_r1.py`) with the project closed; accept LabVIEW's own BOM and line endings. AIXML
  sources (`.xml`) are text and may be edited. (pilot rules 12, 34) > MCP-candidate: project-item-tools
- Item URLs in a `.lvclass`/`.lvlib` are relative to the file itself, as if it were a folder level: `URL="../X.vi"` in
  `C\C.lvclass` is `C\X.vi`. Remove a library's item **before** deleting its file (else the modal search dialog).
  Never hand-write `NI.Lib.ContainingLib`; membership goes through `lvai_add_to_library`. (pilot rules 4, 12, 70)
- Write AIXML and scripts with an editor tool, never a shell heredoc: one turned `\\2C` into byte 0x02 and the convert
  refused the file. (pilot rule 69)

### Evidence, git, build order
- **`ok: true` from a writing tool is not evidence.** Only `lvai_exec_state` read cold (project closed) sees `eBad`:
  check after every structural step. Check membership too: a VI that silently stopped being a class member also reads
  state 1. A sweep needs a negative control (a missing path reads `0 7`). (pilot rule 1)
  > MCP-candidate: exec-state-batch
- **Commit before every structural step** (class, field, member, override, hook, library, message, regeneration,
  removal), by explicit paths: the tools rewrite files and discard layout, icons and decorations without asking.
  **Close the project before any `git restore`/`checkout`/`revert`/`reset`** of LabVIEW files. A small re-save by
  LabVIEW (some bytes smaller, state still 1) is LabVIEW clearing leftovers: commit it. (pilot rule 12)
- **Build order inside a library:** class, typedef field binding, accessors, methods, pane-typedef binding, LIBRARY,
  messages, overrides. Library membership rewrites the qualified name and `Do.vi` calls the method by that name; the
  tell is `Do.vi` broken and `Send` fine, the repair is to delete and regenerate the messages. Hook VIs exist before
  they are hooked; a hook that sends its own actor's message keeps its `Send` placeholder until the message exists.
  **Never author `Do.vi`:** `lvai_create_message_class` drives NI's Message Maker. (pilot rules 2, 3)
- labview-mcp's own agents do not know these rules, the build order, the library step, folders or icons: brief them
  (`session/brief.md`), and tell the class generator not to hand off to a test framework that is not installed.
  > MCP-candidate: plugin-agent-traps

## Save version

LabVIEW saves a file in the version its library, project or folder names; with none in effect, in the IDE's own
version. A one-VI fix saved from LabVIEW 2026 makes that VI unloadable in the project's older LabVIEW. Saving from the
newer IDE is fine; upgrading the files is not (the user's decision). Route:
1. **Scan before the first save:** `<skill>/kit/lv_save_version.py` reads the version stamp of every file the step may
   save (VIs, `.ctl`, `.lvclass`, `.lvlib`, `.lvproj`). Compare with `project.json` `save_version`.
2. **Make sure the save cannot upgrade them.** NI's **Save version** (LabVIEW 2024 Q3+, back to 17.0, only for items
   that separate compiled code): a library/class's own setting beats the older of the project's and a `.lvversion`
   file's; with none set, the IDE version wins.
   - Where: Project » Properties » Project » Save version, stored in the `.lvproj` as
     `<Property Name="NI.LV.All.SaveVersion" Type="Str">20.0</Property>`; the same property in a `.lvlib`/`.lvclass`
     ("Default" = inherit); or a `.lvversion` file (one line, `20.0`) covering every VI loaded from its folder down,
     which can sit outside the repo, above the checkout. LabVIEW writes the property itself when it closes an older
     source-only project (a side effect to report), and on the first save and close of a new project, with the IDE
     version (26.0 in an evaluation, 2026-10): no script is needed when the IDE version is the save version.
   - To set it: write the property line into the **closed** `.lvproj`, byte-exact, before `NI.LV.All.SourceOnly`. VI
     Server `SetSaveVersion` (input `Version`) exists, is not probed through labview-mcp, and loads every item, which
     then prompts to save on close (a modal). If the skill cannot set it, ask the user to set it first.
3. **Save through the open project.** Saves with the project open kept their 2020 version; saves with **no project
   open** went to 26.0, VIs and `.lvclass` alike (Clean Up Diagram and icon helpers run cold). Unverified: whether
   `Save.Instrument` on a VI opened by path, not through the project, follows the project's setting. Helpers that must
   run with the project closed (icons, cleanup, re-save, property setters) would upgrade code older than the IDE. A
   `.lvversion` over the tree or a library/class Save version may prevent that (documented by NI, not measured here).
   When such a conflict comes up, ask the user before the save.
4. **Re-scan after the step.** Any file newer than `save_version`: stop and report; restore it from git with the
   project closed. Never use Save for Previous (it writes lossy copies).
5. Every version change and every Save version written goes into the end report's side effects.
[LabVIEW 2026 Q3, labview-mcp 1.8.5; audit rule candidate 100] > MCP-candidate: save-version-check

## Known gaps by tool

Each gap: effect, workaround, version measured. Long routes are in the ops files named.

### lvai_status, lvai_ensure_labview
- The AI gRPC service lives in `LabVIEW.exe`, but it **starts with Nigel, not with the IDE**: a freshly started
  LabVIEW can run for many minutes without serving `lvai.LVAI` until the Nigel chat has been opened (labview-mcp's own
  tool description, 1.8.5). Once the service is up, it keeps answering when the chat window closes (pilot rule 99,
  H19/H21). The start route, including opening Nigel unattended, is `session/start.md`. While a helper runs past its
  deadline `lvai_status` cannot answer. [1.8.5] > MCP-candidate: deadline-abort, ensure-labview-complete
- `lvai_ensure_labview` only starts LabVIEW; no tool stops or restarts it (`session/restart.md`). On a cold start it may
  spend its 40 s budget and answer `ok:false`, "starting", "The operation was canceled." although the start worked:
  call `lvai_status` next, not `ensure_labview` again. It clears `LVAutoSave` (from the real, possibly redirected
  Documents folder) when it starts LabVIEW itself; `keepAutoSave: true` opts out, but then a recovery dialog blocks
  the service. [1.8.5] (pilot rule 96) > MCP-candidate: restart-with-guards, ensure-labview-complete

### lvai_exec_state
- "VI has an error of type 8" on a class member can mean the class implements an interface without overriding one of
  its methods: check the overrides before a sweep of the callers. [1.9.5, a harness run 2026-10]
  > MCP-candidate: clearer-answers
- One VI per call. A tree needs the kit sweep (`pa_exec_state_sweep_file.xml`, `sweep_paths.py`) and a file-side
  membership check (`check_membership.py`): `ops/sweep.md`. The helper reloads each VI's library per VI, so where the
  hierarchy does not resolve a VI costs > 1 s, up to ~30 s, against 51–97 ms where it does. Size batches from a timed
  first batch (CS-1, open in the audit). [1.8.5] (pilot rule 1; audit rule candidate 108)
  > MCP-candidate: exec-state-batch
- It reads the default instance only: a VI running in a project's instance is not seen, and nothing measured detects
  a running top-level VI. > MCP-candidate: memory-inspection

### lvai_run_vi_and_read_values
- Refuses an empty input value: omit the input. [1.8.0] (pilot rule 47)
- Returns the whole panel: test VIs that show their data answered 111–519 KB, one over the gRPC message limit
  (`ResourceExhausted`) although the VI ran. Use a wrapper VI that returns only Pass and `error out`. [1.8.5]
  > MCP-candidate: read-named-indicators
- `values["error out"]` is the target VI's error; `errorCode`/`helperErrorCode` are the runner's.
- `runForMs` runs a never-ending VI for N ms, reads a snapshot, then **aborts** it with no cleanup: not a stop (and
  actors a launcher started run on as their own VIs, reasoned). [1.8.5] > MCP-candidate: run-vi-async

### lvai_run_vi_as_top_level
- Synchronous: a VI that never returns blocks the service; on an AF launcher it answered `errorCode 91` although the
  tree started. Start such a VI with the kit's `pa_run_vi_async.xml` (Run VI, Wait Until Done F; it cannot set
  controls). A stopped top-level VI whose panel was opened stays in memory (state 1, not 1004) until `pa_close_panel`.
  A control off the connector pane keeps its value only while the VI stays in memory; two tool runs unload it.
  Routes: `ops/run-checks.md`. [1.8.0] (pilot rules 57, 63) > MCP-candidate: run-vi-async
- No tool reads a control of a running VI or presses a button: kit `pa_read_control(_u32).xml` (1004 = left memory)
  and `pa_press_control_signal.xml` (`Value (Signaling)`). [1.8.0] (pilot rules 25, 35)
  > MCP-candidate: read-running-vi > MCP-candidate: press-control

### lvai_generate_vi, lvai_convert_aixml_to_vi, lvai_convert_vi_to_aixml, lvai_validate_aixml
- `lvai_convert_aixml_to_vi` does not create the target folder; the miss reads `Error 7 … Save:Instrument`, and a
  failed save may block that file name (1051). `lvai_generate_vi` creates it since 1.8.5. [1.7.2–1.8.5] (pilot rule 13)
  > MCP-candidate: convert-target-folder
- A failed convert burns the document's `_name` until LabVIEW restarts: probe under another name first
  (`<skill>/kit/make_probe.py`). `lvai_generate_vi` converts under a throwaway name itself since 1.8.5. (pilot rule 24)
- Class wires: `lvai_generate_vi` refused them ("connected two terminals of different types") in VIs that call
  `Launch Root/Nested Actor`, `Send …` or `Read Self Enqueuer`. Route: `lvai_convert_aixml_to_vi` with placeholder
  stubs, then `lvai_swap_subvis` (a socket used twice costs two swaps; an empty VI is ~3 kB). A VI that calls library
  or class members converts without stubs when the project is open and one member is opened through it (only class
  constants then need swaps); labview-mcp 1.8.5 documents this and does it inside `lvai_generate_vi`: re-check before
  using stubs. A probe convert under another `_name` is adopted into the `.lvproj` (drop it with `lvproj_drop.py`).
  [1.7.2; 1.8.0] (pilot rules 8, 50) > MCP-candidate: generate-calls-loaded-members
- `lvai_validate_aixml` refuses `To More Generic/Specific Class` on path stand-ins ("Polymorphic terminal cannot accept
  this data type"), a false positive: convert with `validateFirst: false`, let `lvai_exec_state` decide. Since 1.8.5 the
  convert repairs reserved-range uids (< 4200) and refuses invalid XML characters (`notWellFormedXml`). (pilot rule 56)
- `lvai_convert_vi_to_aixml` does not create its target folder (`Error 7 … Write to Text File`); `lvai_convert_vis_to_aixml` (a list) does.
  [1.8.5] (pilot rule 75) > MCP-candidate: convert-target-folder
- The export carries no mechanical action, no visibility and no element for the event structure's dynamic terminal:
  read those cold (`pa_read_boolean`) or offline from the nets (`<skill>/kit/vi_nets.py`). An AIXML source beside a
  VI can be older than the VI (scripted hooks are not in it). [1.8.5] (pilot rules 60, 82) > MCP-candidate: nets-dump
- A VI that is a member of a LOADED library cannot be regenerated over its path: `lvai_generate_vi` answers 1357.
  Project closed, `remove_members.py <.lvlib> "<vi>"` (no `--delete-files`); then open, generate, swap, and
  `lvai_add_to_library` again. Prefer an in-place edit for a small fix ("Small fixes: edit in place"). [1.9.5, a
  harness run 2026-10]

### lvai_placeholder_subvi, lvai_swap_subvis
- The placeholder for an array-of-class terminal is a scalar `path`, so Array Size or Index Array cannot be wired.
  Make that stub by hand with `array{path}`; after the swap the loop, shift register and array nodes re-type.
  [1.8.0] (pilot rule 53) > MCP-candidate: placeholder-array-of-class
- A placeholder of a typedef-cluster accessor may fail with "error 1154 from Invoke Node in lvai_typedef_bind.vi …
  Replace"; the stub still works with the bare cluster. [1.8.5]
- One stub shared by several nodes (Case frames, two top-level calls): "newest node first" is not reliable. Swap,
  export, check where it landed (`aixml_frames.py`), correct by swapping with `socket` = the real VI's qualified name.
  A real member swaps straight onto another member with the same pane, keeping series wiring, also inside a
  flat-sequence frame. [1.8.0–1.8.5] (pilot rules 38, 71, 72) > MCP-candidate: swap-subvis-fixes
- Cannot repair a missing-subVI node: its name reads empty, the call fails with 1055 reported as `noActiveProject`.
  Repair: `lvai_close_vi`, re-run `lvai_add_class_method` from the AIXML, swap. [1.8.5] (pilot rule 86)
  > MCP-candidate: swap-subvis-fixes
- `constantsJson` finds TOP-LEVEL constants only: a class constant inside a case frame needs a deep replace
  (`kit/pa_replace_constant_deep.xml`, input `class path`). With the swap's `class` = a `.ctl` path it turns a bare cluster constant into that typedef's
  constant, which `lvai_bind_typedef_constants` cannot (it needs a subVI terminal). Depth: measured 2 levels (While >
  Case), written for 3 (evaluation 2026-10). [1.9.5, a harness run 2026-10]
  > MCP-candidate: swap-subvis-fixes
- The placeholder for a typedef cluster that holds a class flattens it to a scalar `path`, and members with the same
  pane get ONE shared stub, so a swap cannot tell them apart: make one stub per target by hand. [1.9.5, a harness run 2026-10]
  > MCP-candidate: placeholder-array-of-class
- `lvai_bind_typedef_constants` with a bare `subViName` answers 1055 "no active project" when it means "name not
  qualified": pass the library-qualified name. [1.9.5, a harness run 2026-10] > MCP-candidate: clearer-answers

### lvai_create_class, lvai_create_interface
- With a parent class, the PARENT is added as a top-level `.lvproj` item: drop it right after (`lvproj_drop.py`,
  project closed). The class's own top-level entry usually goes at the library step, not always: check the `.lvproj`.
  [1.8.0–1.8.5] (pilot rule 54) > MCP-candidate: project-item-tools
- `typedefFieldsJson` puts typedef fields after the plain `fields`, in JSON order. Binding an array-of-class field
  inside `lvai_create_class` **crashed LabVIEW**: placeholder, commit, bind in a separate call. [1.8.0] (pilot rules
  37, 51) > MCP-candidate: typed-add-class-field
- `parentInterfaces` links interfaces at creation (no tool adds one later: NI's provider is a modal). A class must
  override every interface method, or the class is error 1003; interface overrides are ordinary
  `lvai_add_class_method` members with the same name and pane. (pilot rules 9, 10)
- It writes the `.lvproj` with LF line endings and no BOM; a later project close may restore the BOM. Accept what
  LabVIEW writes and check only the item lines: do not restore the `.lvproj` from git after each step (a harness did
  it about 30 times in one session). Check once whether the repo's `.gitattributes` forces `eol=lf` on
  `.lvproj`/`.lvlib`/`.lvclass` while LabVIEW writes CRLF: that would cause the same churn (suspected, not measured).
  [1.9.5, a harness run 2026-10] > MCP-candidate: close-project-guard

### lvai_add_class_field
- Plain AIXML types only (`string, timestamp, path, bool, double, single, int8..uint64`): no cluster, array, enum or
  class; add a placeholder, then bind (`ops/class-field.md`). It appends. `fromField: -1` resumes from the member count,
  wrong on a class with methods: pass `nextFromField`. [1.8.0–1.8.5] (pilot rules 29, 37, 51)
  > MCP-candidate: typed-add-class-field
- No tool removes a field: labview-mcp's `lvpdc_export`, delete by label, `lvpdc_import`, re-save every member
  (`ops/class-field.md`). [1.8.5] (pilot rule 68) > MCP-candidate: remove-class-field

### lvai_create_typedef, lvai_resave_ctl, lvai_describe_ctl
- No class element in a cluster and no default value: a cluster `{protocol: <class>}` or a U32 with default 500 needs
  a derived VI Server helper after the create (defaults: `ops/class-field.md`, step 2, before the membership and the
  bind). [1.9.5, a harness run 2026-10]
  > MCP-candidate: typedef-class-element-default
- A `projectPath` other than the active project closes and saves the active project (a pilot project re-saved, 5 stray
  entries swept): pass the active project, or none. [1.8.5] (pilot rule 67) > MCP-candidate: close-project-guard
- `overwrite: true` on a library's typedef drops it from the library (callers: "Missing typedef …"): repair with
  `remove_members.py` on the `.lvlib`, then `lvai_add_to_library`. The typedef's label is its file name, so an
  accessor's value terminal is named after the `.ctl`: read names with `lvai_vi_terminals`. [1.8.0] (pilot rule 48)
- A `.ctl` LabVIEW never saved gives Error 1061 in the accessor wizard: after a fallback build (`lvai_generate_vi` +
  `patch_ctl.py`), `lvai_resave_ctl`, then `lvai_describe_ctl` = `wrappedType TypeDef`. [1.7.2] (pilot rule 7)
- Spellings that work: `uint16{Off,On}`, `ref{UserEvent}{bool.stop}` (the suffix labels the element),
  `cluster{ref{UserEvent}{bool.stop}.stop,ref{UserEvent}{string.error}.error}`, `array{bool.<name>}`, `ref{UDP}` (not
  in `lvai_aixml_reference`). (pilot rules 51, 66) > MCP-candidate: vi-server-catalogue

### lvai_bind_class_fields, lvai_bind_pane_typedef, lvai_coercion_dots
- Bind before any accessor: an accessor made earlier keeps the bare type for ever. The `accessorsAlreadyPresent`
  warning counts every accessor of the class: it matters only if this field's own accessors exist. [1.8.5]
- A class-typed field binds with `ctlPath` = the `.lvclass` and `force: true`; the answer is `ok: false` by design, and
  `lvai_describe_class` shows `Refnum`, `RefType=UDClassInst`. [1.8.0] (pilot rule 29)
  > MCP-candidate: typed-add-class-field
- After a failed step it runs the next one anyway (an import after a timed-out export: a second 300 s wait), and its
  note blames a `.ctl` that was a typedef. Read the steps, not the note. [1.8.5] > MCP-candidate: bind-fields-step-errors
- `lvai_coercion_dots` read `subViCalls: 0` on 10 of 10 VIs: prove a pane binding from the files (typedef heap objects
  0 to 1). `lvai_bind_pane_typedef`'s `typedefInSavedFile` can pass before the bind. [1.7.2] (pilot rule 15)
  > MCP-candidate: coercion-dots-blind

### lvai_create_accessors
- One `dynamicDispatch` for the whole run: it keeps slicing to the end of the class, and a private dynamic-dispatch VI
  is broken ("error of type 2000000"). Per-field settings: one slice at a time, `fromField` = the field index,
  `fieldCount: 1`, `budgetSeconds: 1`. `virtualFolderName` creates the folder and puts the pair in it. [1.8.0–1.8.5]
  (pilot rules 30, 36, 84) > MCP-candidate: accessor-options

### lvai_add_class_method
- Re-run on a method a loaded member calls (an override hook or a plain caller): Error 56003 **after** the member entry
  was dropped. Unhook (swap the callers onto a placeholder), regenerate, swap back. One name stayed held after every
  caller was unhooked: then add the new behaviour as a new hook. Since 1.8.5 a re-run drops the existing members first
  (`dropExistingMembers`), with no 56003 when nothing holds the VI. [1.7.2–1.8.5] (pilot rules 22, 49)
- A failed convert inside a re-run leaves the member dropped: fix the AIXML, re-add, `check_membership.py`. A re-add
  resets the scope to public and moves the VI out of its virtual folder: `set_scope.py` (project closed) and the folder
  again, check with `lvai_describe_class`. [1.8.0–1.8.5] (pilot rules 56, 69)
- With `aixml` AND `vi` it re-converts the VI from the AIXML: dynamic event wiring, user-event specs and event data
  fields are lost. To make a built VI a member pass `vi` only (with `classTerminals`). [1.8.5] (pilot rule 91)
  > MCP-candidate: add-class-method-rerun
- A member with NO class terminal on its pane (a pure function) is refused here (no `classTerminals`) and by
  `lvai_add_to_library` (refuses a `.lvclass`). Route: `lvai_generate_vi`; `lvproj_add_toplevel.py` (project
  closed); the tool's cached helper `lvai_add_one_to_library.vi` with `library path` = the `.lvclass`, item type VI,
  folder index -1 (project open and active); then `set_scope.py`. [1.9.5, a harness run 2026-10]
  > MCP-candidate: add-to-class
- `ok: false` with `pathStandInsLeft` for a path stand-in INSIDE a cluster terminal is a false alarm when a later
  pane bind resolves it: read the state after the bind. [1.9.5, a harness run 2026-10]
  > MCP-candidate: clearer-answers

### lvai_add_to_library
- Refuses a virtual folder that does not exist, and a new library has none (`Controls` included); no tool creates one.
  `{LV.Library}` `AddItem` (Type `Folder`) creates one in a class (`kit/pa_class_folder_create_and_move.xml`); on a
  `.lvlib` it is the same class but unmeasured: try it on a throwaway before asking the user.
  [1.8.5] (pilot rule 92) > MCP-candidate: library-virtual-folder
- One add re-saves every member of the library (11 files: all 7 VIs, the class, the other `.ctl`), each a save that can
  change its version. No tool adds a `.ctl` to a class (kit route: "Class description, typedef membership, virtual folders" below). [1.8.5] (audit rule candidate 106) > MCP-candidate: add-to-class
- Messages go one folder each into `Messages for this Actor` (folder name; check `placedIn`). A
  `projectEntriesToRemove` for a `.ctl` the `.lvproj` never listed needs nothing. (pilot rule 20)
- After any library add or Save All (`pa_save_libraries`): `git status --short` over the tree. A re-save outside
  the task's scope (a test VI re-saved by 1 byte, a harness run 2026-10) is a side effect: restore it with the project closed or
  report it; never commit it blindly.

### lvai_create_message_class, lvai_describe_class
- The kit's Message Maker helper (`lvai_create_message_class.xml`) writes the message class FLAT into its
  `destination directory`: create the empty `<Msg class name>\` folder first and pass it as the destination.
- Message payload = every method input other than the class and the error cluster, in pane order (descending
  `conIdx`); String and class payloads work. For an **interface** method the tool refuses: run the kit's
  `lvai_create_message_class.xml` directly, then `repair_r1.py`. [1.8.0] (pilot rule 19)
  > MCP-candidate: message-interface-method
- `lvai_describe_class` misreports a class derived from LabVIEW Object (rename history shown as ancestors): read the
  `.lvclass` XML. [1.7.2–1.8.0] (pilot rule 16) > MCP-candidate: describe-class-ancestry

### lvai_generate_vi_with_events, lvai_wire_dynamic_events, lvai_set_event_data_fields
- A plain AIXML convert loses every event frame: use `lvai_generate_vi_with_events`, which refuses two Event
  Structures in one document. [1.8.0] (pilot rule 39)
- The dynamic event terminal has no AIXML element. An authored refnum tunnel makes `lvai_wire_dynamic_events` branch a
  plain tunnel (the wrong shape). Author no refnum tunnel, wire the left side with `finishUserEvents: false` (the
  diagram route) and the right side with `pa_wire_dyn_right.xml`. [1.8.5] (pilot rule 60)
  > MCP-candidate: wire-dynamic-events-fix
- It searches two levels: an event structure in a case frame inside the loop (three levels) gets Error 91 /
  `helperDidNotAnswer` and no change. `kit/pa_wire_dyn_deep.xml` wires both sides at three levels. The right-side
  case tunnel it creates has no value in the other frames and breaks the VI; "Use Default if Unwired" is refused by
  AIXML ("Invalid property"), so `kit/set_use_default.py` sets it in the pylv round trip (state 1 with it, 0 without).
  [1.8.5, measured 2026-10] > MCP-candidate: wire-dynamic-events-fix
- Its finish step refuses more than one user event, is skipped on the diagram route (Error 91 / `helperDidNotAnswer`,
  `wireEndsAfter 2`: expected), and with the default `finishUserEvents` closes and saves the active project. After a
  load every user-event spec has `dynIndex` N+1. Write the specs with `set_user_event_specs.py` between `pylv_extract`
  and `pylv_rebuild` (`dynIndex` = the source's 1-based position on `Register For Events`). labview-mcp's
  `pylv-set-event-spec.py` documents a `[dynIndex]` it does not take. [1.8.0–1.8.5] (pilot rules 39, 60)
  > MCP-candidate: wire-dynamic-events-fix
- An event structure whose frames are all user events fails the spec step ("no dIdx on this event structure"): add an
  empty Timeout frame (a build-step limit, not LabVIEW's). `lvai_set_event_data_fields` on a VI not yet a member
  answers `ok:false`, state 0: expected until membership and swaps. A frame selector takes the refnum or cluster
  **element** label (` <stop>\3A User Event `). Panel flags: see the scripting quirks. [1.8.0–1.8.5]
  (pilot rules 39, 62, 65, 66) > MCP-candidate: generate-with-events-fixes

### lvai_set_vi_icon and icon work
- It sets the VI's own layer and **flattens** the icon: editable text layers are lost (27–36 % of hand-made icons
  changed). Run it before the class template, never on a VI whose own layer is to be kept. [1.8.0–1.8.5] (pilot rule
  26; audit rule candidate 110) > MCP-candidate: set-vi-icon-keep-layers
- Class and library icons have no tool; kit route in `ops/icons.md` (`Set Icon`, then `ApplyIconToVIs` + a save per
  member). With the project open: 1562, nothing written. `ApplyIconToVIs` alone does not save the members. On a plain
  `.lvlib`, `Library.Open` does not load the members and the apply silently changes nothing: open them first. [1.8.0]
  (pilot rules 26, 42) > MCP-candidate: class-library-icons
- `Set Icon` answered 1562 on one class with nothing visibly locked, also after a project open/close. A LabVIEW restart
  with that class call first cured it (probably held in memory by an earlier `LVClass.Open`). Fallback:
  `lvai_set_vi_icon` with each member's composite PNG (looks the same, no `NI_Library` layer). [1.8.0–1.8.5] (pilot
  rule 59)
- `Save VI Icon to File` writes nothing and returns no error into a missing folder or for a path over MAX_PATH (~260
  characters): use a short folder (`%TEMP%\LabVIEWMCP\rb`), count the files. [1.8.5] (pilot rule 80)
  > MCP-candidate: icon-readback

### lvai_vi_server_reference, lvai_aixml_reference
- `BD.CleanUp` (`{LV.VI}` Invoke: Clean Up Diagram) is missing from the catalogue, and so are the Project and Library
  classes (Save, Close, `SetSaveVersion`). Find spellings in NI's exports (`examples\Application Control\VI
  Scripting\`) or in LabVIEW's `resource\lvserver.rsc` (class and member names as plain text; search it with grep);
  never guess. [1.8.0–1.8.5] (pilot rules 14, 46)
- **Never probe an unknown name with `lvai_validate_aixml`.** An invented method on `{LV.Application}` crashed LabVIEW
  2026 Q3 inside the validator (DWarn in `invoke.cpp`, 2026-10). Validate only names found in one of the sources
  above. A real name can still be refused by the AIXML catalogue ("Invalid property", e.g. "Use Default if
  Unwired"): that is a refusal, not a crash, and the pylv route is next.
  > MCP-candidate: vi-server-catalogue

### No tool yet (kit routes only)
- AF overrides and hooks, `ops/override.md` > MCP-candidate: create-override; > MCP-candidate: add-hook
- Member rename, `ops/rename.md` > MCP-candidate: rename-member
- Clean Up Diagram, `ops/cleanup.md` > MCP-candidate: cleanup-diagram
- Front-panel properties, `ops/helper-loop.md`; VI descriptions, "LabVIEW scripting quirks"
  > MCP-candidate: control-property-setters
- Restart LabVIEW, `session/restart.md` > MCP-candidate: restart-with-guards
- An actor's wiring without exports, `ops/review.md` > MCP-candidate: af-describe-actor
- Class description, a `.ctl` into a class, a member into a virtual folder: "LabVIEW scripting quirks", "Class
  description, typedef membership, virtual folders" > MCP-candidate: class-description;
  > MCP-candidate: add-to-class; > MCP-candidate: move-to-folder
- **A new project or a plain library** (no tool; `lvai_lvproj_reference` calls `.lvproj` generation unsupported).
  Measured VI Server spellings (a harness run, 2026-10), in a helper VI:
  - `.lvproj` (no project needs to be open): `{LV.Application}` Invoke `Project.New` (outputs `Project\3ANew`) →
    `{LV.Project}` read `My Computer` → `{LV.TargetItem}` Invoke `AddItem` (inputs `Name`, `Path`, `Type` = `Folder`;
    `Path` must be an EMPTY path) per virtual folder → `{LV.Project}` Invoke `Save` (input `Path`) → `Close`. NI's
    example `Manipulating Projects\Add Files to Project.vi` carries the spellings. `lvai_describe_project` does not
    list virtual folders: check them in the `.lvproj` XML. Helper: `kit/pa_new_project.xml`.
  - Plain `.lvlib`, project open and active: `{LV.Application}` Invoke `Library.Create` (output `Create Library`) →
    `AddItem` (Type `LVClass` or `VI`) per item → `{LV.Library}` Invoke `Save` (input `Path`) or `Edit
    LVLibs.lvlib:Save All This Library.vi` (the kit's `lvai_create_actor_library.xml` is the model). A loose VI must
    be a project item first (`lvproj_add_toplevel.py`, project closed), or the close writes no library and drops the
    entry. An empty library: `kit/pa_new_library.xml`. The close does NOT list a new library that is empty: add it
    with `{LV.TargetItem}` Invoke `AddFile` (input `Path`) on `My Computer` (`kit/pa_project_add_file.xml`), project
    open and active, then close and `lvproj_move.py` it into its folder. A library
    holding a class may come back at top level plus a stray class item: `lvproj_drop.py` and `lvproj_move.py`, project
    closed. (measured in an evaluation, 2026-10) > MCP-candidate: project-item-tools

## LabVIEW scripting quirks

They hold for any VI Server or AIXML route, the kit's included.
- **AIXML cannot author** `Call Parent Class Method` (so an override is never regenerated; its body is scripted), a
  mechanical action, a chart's history length or plot names, a `.ctl` reference (use a bare cluster with the same
  names), or the dynamic event terminal. `Format Into String` has one input. It can author a `Local Variable` node
  (`<Node _name="Local Variable" element="stop" outputs="stop:N.stop"/>`; `inputs=` writes), a `<Condition
  value="stop">` on a For loop, and a waveform chart (`style="graph21717"`). A placeholder of a pane-less VI is a
  `<Call>` with no inputs or outputs. (pilot rules 24, 44, 45, 53, 57, 61)
- **Panel flags are lost on regeneration:** `Show Front Panel On Call`/`Close After Call` survive
  `lvai_add_class_method` with `vi` only, the pylv rebuild and swaps, not a convert over the path. Re-apply, read back
  cold. **Mechanical action** is not settable from AIXML and the export shows neither it nor visibility: set by VI
  Server, prove by a cold read. A latch is not writable by VI Server (1193) and a value write fires no Value Change
  (`knowledge/actor-framework.md`). (pilot rules 35, 40, 57, 65, 82)
- **AIXML traps:** `Equal?` on two clusters is generated in Compare Elements mode (a cluster of Booleans): follow it
  with `Cluster To Array` → `And Array Elements` before a Boolean array or indicator (`vi_nets.py` shows it offline).
  `Match Regular Expression` is an XNode and cannot be authored: use `Match Pattern` with an anchored
  character-class pattern. (a harness run 2026-10)
- **Plot names** (no AIXML element): `{LV.WaveformChart}` `Active Plot` → `Plot` → `{LV.Plot}` `Plot Name`, project
  closed, `Save.Instrument` (`kit/pa_set_plot_names.xml`); spellings from `lvserver.rsc`. **A panel text label:** `New VI Object` style 2321 (Free
  Label) answered 1060 in every owner/class tried; style 21960 (Label (modern)) works but draws a framed label.
  (a harness run 2026-10) > MCP-candidate: control-property-setters
- **A class save may double the line breaks in `NI.LVClass.Geneology`** (`\r\n` → `\r\n\r\n`): harmless diff noise; do
  not hand-fix it. (a harness run 2026-10) A class's first save after `lvai_create_class` rewrites the whole
  `.lvclass` (line endings, plus Geneology): a 45-line diff for one property (evaluation 2026-10).
- **Reentrancy:** the VI Server write `Execution:Reentrancy Type` + `Save.Instrument` answered no error and changed
  nothing. Set `IsReentrant` + `PooledReentrancy` in a pylv bundle (`set_reentrant_flags.py`, project closed). To read it: `Execution:Reentrancy Type` = 0 also for a shared-clone VI; read `Execution:Is Reentrant` with it.
  (pilot rule 52)
- **VI description:** read `VI Description`, replace, write, `Save.Instrument` (project closed) keeps the icon, layout
  and state 1 (`pa_replace_description.xml`); edit the `.xml` source as text. (pilot rule 81)
- **Class description, typedef membership, virtual folders** (VI Server, project open and active; measured on LabVIEW
  2026 Q3 32-bit, 2026-10-11/12, on 15 classes). The names are not in `lvai_vi_server_reference`; they come from
  LabVIEW's `resource\lvserver.rsc`. **Description:** `LVClass.Open` on the project's application, write
  `{LV.LVClassLibrary}` `Description`, read back, `Save` (`kit/pa_set_class_description.xml`). It is stored ANSI
  (CP1252): "→" became "?" with no error, so write ASCII and read back. **Folder:** `{LV.Library}` `AddItem` (Type
  `Folder`); **member into it:** `{LV.ProjectItem}` `Move` (`New Parent` = the folder item)
  (`kit/pa_class_folder_create_and_move.xml`, `pa_class_folder_move.xml`). A move changes only the `.lvclass` (no file
  move, no rename, no relink): routine, no question. **File into a class:** `{LV.ProjectItem}` `AddItem` (Name, Path,
  Type) on the folder item (`kit/pa_class_folder_add_files.xml`). **A `.ctl` added to a class is renamed**
  (`Class.lvclass:X.ctl`) and every caller relinks: add it right after it is created, before anything uses it. Added
  later: open every caller outside the class through the project first (so it relinks in memory), add, then
  `kit/pa_save_libraries.xml` on each library whose members use it and `kit/pa_project_vis_modified.xml` (`save
  modified?` T) for top-level VIs (on a large project its answer is saved to a file: read it with
  `kit/mem_lines.py`). A `.ctl` saves only through a library Save All (`Open VI Reference` answers 1035).
  LabVIEW makes the added typedef public. A harness permission check may stop the typedef add as a shared-resource
  change while it allows the moves. > MCP-candidate: class-description; > MCP-candidate: add-to-class;
  > MCP-candidate: move-to-folder
- **Clean Up Diagram and Remove Bad Wires keep a helper-loop VI's dynamic event wiring, user-event specs and
  use-default tunnels** (measured, a harness run 2026-10): no probe needed before cleaning one.
- **Clean Up Diagram** (`{LV.VI}` `BD.CleanUp` + `Save.Instrument`, project closed) keeps classes, state, icon and the
  AIXML export; 0.25–0.8 s per generated VI, 4–5 s on older trees. A regeneration discards it. On a hand-laid diagram
  it can grow it (1160x495 to 1290x925): `convention: hygiene` says where it runs. (pilot rule 46; audit rule candidate 109)
- **Rename** = `Save.Instrument` to the new path with the class and every caller loaded in the project's instance. The
  old file stays, string references are not updated, and a caller not loaded keeps the old link silently (helper 0,
  caller state 0 cold, no dialog). (pilot rules 64, 85)
- **Call Parent** is class `CallParentNode`, not in `SubVIs[]` (the kit AF helpers' subVI lists do include it): find
  it by its `Actor out` terminal over `All Objects[]`. Scripting cannot wire into a bare structure frame: wire to an
  inner terminal, then delete that inner wire. `New VI Object` for a structure needs `vi object class` and `style`
  (Flat Sequence: `ref{LV.FlatSequence}`, style 2069); with neither `style` nor `path` the AIXML refuses the node, an
  empty `path` answers 1059. (pilot rules 76, 77, 90)
- **Remove bad wires first.** A VI at cold state 0 with a broken-wire text after a generate, swap or bind
  (`<terminal> @ <node> | ...`, e.g. `output cluster @ NamedBundler | settings @ SubVI`) usually has a leftover
  broken wire segment, not a type problem. First run `kit/pa_clean_member.xml` (Remove Bad Wires + save of the VI and
  its class, project open and active) and read it cold; rebuild only if that fails. Measured 2026-10: one run fixed
  (state 0 → 1) a VI that five rebuilds and a LabVIEW restart had not. > MCP-candidate: swap-subvis-fixes
- **Whole VI descriptions in a batch:** `kit/pa_set_vi_descriptions.xml` (project closed) writes many at once from a
  record file and reads each back; for a search-and-replace inside one description, `pa_replace_description.xml`.
- **A path-less VI blocks the project close** after a convert failed at save (Error 1019): `kit/pa_save_orphan.xml`
  saves it by name to a path, then the close works.
- **Small fixes: edit in place, not by regeneration.** A change of a few wires or nodes in a VI whose layout, icon,
  panel flags, description or membership a regeneration would lose is a VI Server edit of the existing VI (a kit
  helper or one derived from it), in the project state the helper names ("Project open or closed"; most are open
  and active, `pa_wire_by_label` runs closed). It needs no `remove_members`, no library re-add
  and no `git checkout` (which a harness permission check may refuse). The pattern, measured on four fixes 2026-10:
  an `apply` input, F first (a dry run that only counts what it finds: every node and wire exactly once), then T;
  every lookup before any delete, and a node's wires deleted before the node (both orders the other way round
  raced: a lost lookup, a loose wire); `python <skill>/kit/vi_nets.py` before and after, the diff showing only the
  intended wires; `pa_clean_member.xml` if a loose end remains; cold state 1. Wiring two nodes by label (primitives
  included), with that dry run: `kit/pa_wire_by_label.xml`; it reads no wire back, so check the wire with
  `kit/vi_nets.py` (1 wire, 2 ends; evaluation 2026-10). **An existing loop that should use a new field**
  (e.g. a constant interval replaced by a setting): a small reader member (class in, the field out) added by
  `lvai_add_class_method`, then an in-place edit that places it, wires the class and the value, and chains its
  `error in`/`error out` into the loop's error chain (an unwired error there was a review finding: a failed read gave
  a 0 ms wait and a spinning producer, measured in an evaluation, 2026-10).
- **Deleting a node from a branched wire** leaves a loose end: the VI reads state 0 ("VI has an error of type
  1000088"), and so does a sibling override of the same class; Remove Bad Wires on the edited VI fixes both. The kit's
  delete by terminal name deletes every top-level subVI node with that terminal. (pilot rules 78, 89)
- A hook VI's required inputs must all be fed by the helper's one wire, or the override breaks and only
  `lvai_exec_state` shows it. `Terminals[]` of a subVI node is ordered by pane slot; match by name. (pilot rules 14, 23)
- `CloseMainWindow` on LabVIEW returns False while a VI Server helper runs, and LabVIEW does not exit. (audit rule
  candidate 105)
- A string constant is not visible to `grep -a` on a `.vi` (the diagram is compressed); a subVI link and the VI
  description are. A raw grep also hits inherited help text: grep qualified names. (pilot rule 87)

- **Merge Errors by scripting:** New VI Object with `vi object class` **GrowableFunction**, style **2147** (the palette
  id); the node then reads Class Name "Bundler". `Function` answers error 1057. Pick its inputs as the terminals with
  `Is Source?` = F, in pane order. [LabVIEW 2026 Q3] (skillsaudit M-CLOSE, 2026-10-09)
- **A flat-sequence tunnel with no wire on either side is deleted by LabVIEW.** A helper that deletes a net and then
  wires to "the old tunnel" fails with 1055: rebuild the tunnel by wiring through it again. [LabVIEW 2026 Q3]
  (skillsaudit M-CLOSE, 2026-10-09)
- **The `close` join is scripted by `<skill>/kit/pa_close_join.xml`** (measured 2026-10-09, one run with the project
  active, then `pa_save_member`; ~25 s generate + < 1 s run). `ops/override.md` (shape D-close) has the route. > MCP-candidate: add-hook

## Harness quirks
- Parallel Bash calls share one shell and one working directory: absolute paths everywhere. (pilot rule 18)
- Long heredocs with nested quotes corrupt Windows paths and escapes: write the script or AIXML with the Write tool and
  run the file; a multi-line commit message goes into a file for `git commit -F`.
- A pipe into `head`/`tail` hides the exit code (`${PIPESTATUS[0]}`). A foreground shell `sleep` may be refused;
  PowerShell `Start-Sleep -Seconds N` worked. `Stop-Process` on LabVIEW is refused unless the user allowed it.
- The scratchpad path the harness gives may be an 8.3 short path: write the long form before passing it to LabVIEW.
