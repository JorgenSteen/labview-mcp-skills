# What should move into labview-mcp

Each entry is a labview-mcp gap this skill works around today, and the tool or change that would remove the workaround.
labview-mcp is open source (Zuehlke/labview-mcp); each entry is written so it can be contributed.

**How to use it.** `> MCP-candidate: <id>` marks the passages that work around a gap (`grep -rn "MCP-candidate: <id>"
<skill>`). When labview-mcp ships one: replace each marked passage with a call to the new tool, delete what **Removes**
lists, set the status to `shipped in <version>`, and keep the entry.

**Status:** `proposed` (asked for by this skill's sources), `open in audit` (no longer used: the user settled every
audit proposal on 2026-10-09; kept for the history of older entries), `possibly fixed upstream` (labview-mcp's source
or docs suggest it is covered; no run here confirms it), `submitted` (issue or PR open upstream), `shipped in <version>`,
`partly shipped in <version>` (what is still open follows), `in a fork build only`.

**Contributing upstream** (the user's decision, 2026-10-09). The candidates stay in this skill until labview-mcp
ships them. What goes upstream is both the candidates (as issues or pull requests) and the knowledge behind them: the
gap descriptions and measured facts in `knowledge/labview-mcp.md`, in the form of labview-mcp's own `docs/*.md`.
- Check each one against the newest labview-mcp release first, not against the old local checkout.
- Nothing is sent without the user's go-ahead for that batch, since it publishes to an outside repository.
- After a send, set the status to `submitted` with the link.

**Baseline:** the entries were measured with labview-mcp 1.7.2 to 1.9.5, each gap with its version in
`knowledge/labview-mcp.md`. **Checked against 2.2.4 on 2026-10-26** from its source and tool texts (not re-run
here): the statuses below say what shipped; much of it came from this skill's own entries, through a fork. Check an
entry against the newest release again before submitting it.

**Evidence ids:** "pilot rule N" = the pilot project's toolchain rules; S1–S10 = its MCP suggestions;
S11–S16, "rule candidate 100–111" and letter-number ids (MC-1, KT-1, ...) = the skills audit (`skillsaudit/`).

## call-lock
**Status** proposed. **Gap** nothing stops two clients calling LabVIEW at once (the client gate guards only the
connect). **Proposed** a server-side queue: one LabVIEW call at a time across clients; a second waits, or answers `busy:
<tool> since <s>`. **Evidence** S9; parallel calls in four pilot sessions; a harness run 2026-10 (two calls in one message in 6 of about 14
steps, read-only ones included). **Workaround** "strictly sequential" in every
brief. **Removes** that rule in `knowledge/labview-mcp.md` and `session/brief.md`.

## deadline-abort
**Status** proposed (MC-1). **Gap** a call past its deadline keeps running in LabVIEW; every later call, even
`lvai_status`, answers `DeadlineExceeded` (~2.5 h once). **Proposed** on deadline abort the helper or answer
`stillRunning: true` with its name; `lvai_status` answers from the service thread with `busy: <tool> since <s>`.
**Evidence** rule candidates 104, 105; S11; CS-2, BR-1, RS-1 (open). **Workaround** no further call; window list and CPU
samples. **Removes** the `DeadlineExceeded` workaround text; the busy route in `session/restart.md`.

## ensure-labview-complete
**Status** partly shipped in 2.2 (`lvai_labview_state` tells not-running and dialog apart; the service comes up with LabVIEW, so Nigel is a fallback only); still open: an `LVAutoSave` count and dry run. Was: proposed. **Gap** `lvai_status` does not tell "LabVIEW not running" from "running, service not up (Nigel
not opened)" or "blocked by a dialog"; `lvai_ensure_labview` starts the IDE but not the AI service, which starts with
Nigel, and it deletes `LVAutoSave` files without saying how many. **Proposed** `lvai_status` answers one of
`not-running` / `running-no-service` / `blocked-by-dialog "<title>"` / `ok`; `lvai_ensure_labview` also opens Nigel
(as `lv_start_nigel_chat.ps1` does: `LVNigelChat.exe --lv-version <v> --lv-bitness <b>`) and reports the `LVAutoSave`
files it found, with a `dryRun` that only counts them. **Evidence** the tool's own description (1.8.5); pilot rules 96,
99; H19, H21. **Workaround** `session/start.md` with `kit/lv_windows.ps1`, `kit/lv_start_nigel_chat.ps1`.
**Removes** steps 2–4 of `session/start.md`.

## exec-state-target
**Status** proposed. **Gap** no tool reads a VI's execution state inside a project target, so a cold sweep never sees
Conditional Disable symbols set on a target. **Proposed** `lvai_exec_state(viPaths, projectPath, target)`, or a
`target` option on `exec-state-batch`. **Evidence** CS-6; Q27; audit D10. **Workaround** none; the sweep report says
which variant it checked. **Removes** the coverage note in `ops/sweep.md`.

## dialog-detection
**Status** partly shipped in 2.2 (`lvai_labview_state`: dialogs with screenshots, no LabVIEW call); answering one (`lvai_answer_dialog`) exists only in a fork build; calls still only time out. Was: proposed (S9); its dependency-check half (MC-2) is covered by `offline-loadability`. **Gap** a modal dialog (`Find the VI
Named …`, a library search, a save prompt, autosave recovery) blocks the service; the agent sees only a timeout.
**Proposed** detect a modal window of LabVIEW and answer `blocked by dialog "<title>"` with its buttons; answer it only
on an explicit confirm. **Evidence** pilot rule 12; rule candidate 103 (720 s); S12. **Workaround** `lv_windows.ps1`;
the user answers. **Removes** the dialog workaround in `knowledge/labview-mcp.md`; dialog guards in `session/restart.md`.

## offline-loadability
**Status** proposed (X-1 settled 2026-10-09; KT-1, MC-2). **Gap** nothing says whether code will load before a call loads it; every
audit hang came from missing packages. **Proposed** `lvai_check_dependencies(paths)`, offline: per VI/class/library
"loadable" or the missing packages and load chain; or `checkDependencies: true` on class-editing tools. **Evidence**
audit G closure (~5 s for 5800 files, predicted every hang). **Workaround** `<skill>/kit/lv_loadability.py` (ported 2026-10-09; a large production tree in ~8 s, same verdict as the audit).
**Removes** the offline-check rule; the loadability steps in `ops/analysis.md`, `ops/sweep.md`.

## close-project-guard
**Status** partly shipped in 2.2 (the tools keep BOM and line endings of their own edits); the active-project check and the side-effect list still open. Was: proposed (S9, S13; MC-3 settled by Q24). **Gap** `lvai_close_active_project` saves and closes whatever
project is active: `projectPath` only names the file swept and is not compared. The sweep removes every item whose file
is missing; the answer does not list what LabVIEW rewrote. `lvai_create_typedef` with a foreign `projectPath` closes and
saves the active project. **Proposed** refuse when `projectPath` differs from the active project (name both); sweep
only items this session added; answer with every side effect (items removed, Dependencies rebuilt, `.lvproj`, `.lvlps`,
`.UserState`, version and BOM); keep the file's own EOL and BOM (`lvai_create_class` writes LF without a BOM, and
agents restored the `.lvproj` from git about 30 times in one session, a harness run 2026-10); name a path-less VI that
blocks the close after a failed convert (1019) instead of failing. **Evidence** pilot rules 67, 83, 95; rule candidate 102; audit M4; CloseTools source
v1.8.0/v1.8.5. **Workaround** check the active project first; commit; report. **Removes** "Opening and closing a project"
bullets 1–2; the side-effect diffing in `session/close.md`.

## project-open-report
**Status** proposed (MC-3, S14). **Gap** opening a large or older project passes the default timeout while the open goes
on, runs App Builder's mutation and rewrites `.aliases`, unreported. **Proposed** `lvai_open_file` answers open time,
item count, dirty flag, files written; on timeout "the open continues". **Evidence** rule candidates 101, 107; L4.
**Workaround** `timeoutSeconds` ≥ 300, then the window list. **Removes** the "opens slowly" bullet.

## project-state-guard
**Status** proposed (S9). **Gap** the wrong project state gives 1055, 1562 or a silently wrong result (state 0 for good
VIs, a `Replace` no-op). **Proposed** each tool declares its state; the server checks first and answers `close the
project first` / `open and activate <project> first`; `lvai_exec_state` says whether a project was open; a read-only
`lvai_active_project`. **Evidence** pilot rules 1, 42, 59. **Workaround** the project-state table. **Removes** that table
and the per-step state lines in the ops files.

## restart-with-guards
**Status** in a fork build only (`lvai_restart_labview`); not in the official 2.2.4. Was: proposed (S2, S9); refinements RS-1, RS-3..RS-5 settled (RS-2 replaced by the user's Q30); KT-5, KT-6 are kit TODOs. **Gap** nothing stops or restarts
LabVIEW; a hung helper loop is freed only by a restart. **Proposed** `lvai_restart_labview(confirm: true)`: refuse and
list unsaved VIs (every instance), dialogs, running VIs; close, tell "busy" from "dialog", start, wait for gRPC, report
port, uptime, steps; optionally reopen the Nigel chat (`--lv-version`, `--lv-bitness`); `ensure_labview` says "still
starting" instead of `ok:false`; discard the tool's own scratch VIs (`LVMCP Validate*`) before the close, and have
`lvai_validate_aixml` close what it opens (they pile up: 8–18 per step, 14 on 1.9.5-local, and any one of them turns
every close into a save dialog). **Evidence** pilot rules 59, 94, 96, 99; rule candidates 105, 111; a harness run
2026-10. **Workaround**
`lv_windows.ps1`, `lv_close.ps1`, `lv_start_nigel_chat.ps1`, `lv_press_ok.ps1`. **Removes** most of `session/restart.md`.

## memory-inspection
**Status** partly shipped in 2.2 (`lvai_vis_in_memory`, every instance, VIs only; classes, libraries and running VIs still open). Was: proposed (S2). **Gap** VI Server memory reads see only the default instance, never classes or libraries,
and no running top-level VI. **Proposed** `lvai_memory(instances: all)`: VIs, classes, libraries, modified flags and
running VIs per instance. **Evidence** pilot rules 59, 96. **Workaround** `pa_vis_in_memory.xml`, `pa_vis_modified.xml`
after the close. **Removes** step 5 and the empty check's memory read in `session/restart.md`.

## exec-state-batch
**Status** proposed; CS-1 settled; KT-8, KT-2 are kit TODOs. **Gap** `lvai_exec_state` takes one VI. **Proposed**
`lvai_exec_state(viPaths | folder)`: state and code per VI, owning libraries held for the batch, a negative control,
file-side membership (owner found walking up), optional `.vim`/`.ctl`, time per VI. **Evidence** pilot rule 1; kit
sweep (116 VIs in 22 s); rule candidate 108 (~30 s per VI when the library reloads); S11. **Workaround**
`pa_exec_state_sweep(_file).xml`, `sweep_paths.py`, `check_membership.py`. **Removes** `ops/sweep.md` steps 2–6.

## cleanup-diagram
**Status** proposed (S3). **Gap** no tool runs Clean Up Diagram. **Proposed** `lvai_cleanup_diagram(viPaths | folder)`,
project closed, code per VI, saved in the project's Save version. **Evidence** pilot rule 46. **Workaround**
`pa_cleanup_diagram(_file).xml`. **Removes** `ops/cleanup.md` steps 3–6.

## create-override
**Status** shipped in 2.2 (`lvai_create_override`; the parent's help text it keeps is replaced with `lvai_set_vi_descriptions`). Was: proposed (S6). **Gap** no tool makes an override with Call Parent; AIXML cannot author Call Parent.
**Proposed** `lvai_create_override(lvclassPath, parentMethod, projectPath)`: library-qualified name derived, Call Parent
placed, parent's scope kept, verified from the files, pane returned; a `description` parameter (it keeps NI's help
text of the parent today). **Evidence** pilot rules 6, 24, 27; a harness run 2026-10 (descriptions replaced in three
steps). **Workaround** `lvai_create_override.xml`; `pa_set_vi_descriptions.xml`. **Removes** "create the override" in `ops/override.md`.

## add-hook
**Status** partly shipped in 2.2 (`lvai_af_add_hook` shapes branch, branchFromNode, series, seriesAfter; `lvai_af_remove_hook`); still open: a series insert on a branched wire, D, D-close, D-append, a node's error output. Was: proposed (S6); the `close` join shape (OV-7) measured 2026-10-09 (`kit/pa_close_join.xml`); PLI failure cleanup (OV-5) settled as the `createResources` member VI.
**Gap** hooks go in through six kit helpers with traps (panel vs node source, swapped roles after Call Parent, delete by
terminal removes every hook). **Proposed** `lvai_af_add_hook(override, class, hookVi, shape, errorWiring)` with shapes
branch, series, series-then-branch, after-call-parent, close-join; it knows each AF pane, returns the wires made, saves
separately. `lvai_af_remove_hook` deletes one node, removes bad wires, re-saves siblings. **Evidence** pilot rules 6,
23, 27, 28, 74, 76–79, 88, 89, 97. **Workaround** `af_add_hook_call(_node)`, `pa_insert_series2`,
`pa_insert_series_branch`, `pa_insert_seq_hook`, `pa_append_seq_hook`, `pa_wire_nodes`, `pa_close_join`,
`pa_remove_series_block`, `pa_delete_subvi`, `pa_clean_member`, `pa_save_member`. **Removes** most of `ops/override.md`.

## add-class-method-rerun
**Status** shipped in 2.2 (`memberHasLoadedCallers` before any change, `rerunNeedsAixml`, `keepPlacement`). Was: proposed (S6). **Gap** a re-run on a called method fails with 56003 after dropping the member; a failed
convert leaves it dropped; a re-add resets scope and folder; `aixml` + `vi` re-converts and loses scripted edits.
**Proposed** unhook, regenerate, re-hook in one call, keeping scope, folder and entry; warn on `aixml` + `vi`.
**Evidence** pilot rules 22, 49, 56, 69, 91. **Workaround** swaps to stubs, `set_scope.py`, `check_membership.py`.
**Removes** the `lvai_add_class_method` gaps; "change a hooked method" in `ops/override.md`.

## typed-add-class-field
**Status** proposed (S4). **Gap** plain types only; a class-typed bind answers `ok:false` by design; an array-of-class
bind inside `lvai_create_class` crashed LabVIEW. **Proposed** accept a typedef, a `.lvclass` or an array of class in one
call (placeholder, bind, verify); report `boundAsClass: true`. **Evidence** pilot rules 29, 37, 51. **Workaround**
placeholder + bind, `pa_array_element_replace.xml`. **Removes** routes 2–4 of "add a field" in `ops/class-field.md`.

## remove-class-field
**Status** proposed (S4). **Gap** no tool removes a field. **Proposed** `lvai_remove_class_field(lvclassPath, fields,
removeAccessors, removeTypedef)`: export, delete, import, re-save members, verify the rest; list callers of the old
accessors. **Evidence** pilot rules 68, 70. **Workaround** `lvpdc_export`, `pa_ctl_delete_fields.xml`, `lvpdc_import`,
`pa_resave_vis.xml`, `remove_members.py`. **Removes** "remove a field" in `ops/class-field.md`.

## accessor-options
**Status** proposed (S4; CF-3 settled: on demand, one direction, private static by default). **Gap** one
`dynamicDispatch` per run, slicing to the class end; a private DD accessor is broken. **Proposed** a `fields` list with
per-field dispatch, scope and direction (whether today's `accessUi` already gives one direction is unmeasured); refuse
private DD. **Evidence** pilot rules 30, 36. **Workaround** `budgetSeconds: 1`, `fieldCount: 1`. **Removes** the slice
recipe in `ops/class-field.md`.

## add-to-class
**Status** shipped in 2.2 (`lvai_add_to_class`, callers relinked and saved; adding a `.vi` unmeasured by labview-mcp). Was: proposed (MC-6, settled). **Gap** no tool adds a `.ctl` or VI to a class; `lvai_add_to_library` re-saves the
whole library. **Proposed** `lvai_add_to_class(lvclassPath, itemPath, virtualFolderName)`, saving only the `.lvclass`.
**Evidence** rule candidate 106; Q17; a harness run 2026-10-11/12 (11 `.ctl` added by VI Server). **Workaround**
`kit/pa_class_folder_add_files.xml`, `pa_save_libraries.xml`, `pa_project_vis_modified.xml` (the caller relink is the
hard part: the tool should load and save the callers). Also a member with NO class terminal (a pure function): both
`lvai_add_class_method` and `lvai_add_to_library` refuse it; the route is the tool's own cached
`lvai_add_one_to_library.vi` on the `.lvclass`. **Removes** those helpers and the notes that cite them.

## library-virtual-folder
**Status** partly shipped in 2.2 (`lvai_move_to_folder` `createFolder`, `.lvlib` arm unmeasured; `lvai_add_to_library` still refuses a missing folder). Was: proposed. **Gap** `lvai_add_to_library` refuses a missing virtual folder; no tool creates one. **Proposed**
`createFolder: true`, for `.lvlib` and `.lvclass`. **Evidence** pilot rule 92; S7. **Workaround** `{LV.Library}`
`AddItem` Folder (`pa_class_folder_create_and_move.xml`; unmeasured on a `.lvlib`).
**Removes** that bullet.

## class-description
**Status** shipped in 2.2 (`lvai_set_class_description`, CP1252 refused before LabVIEW). Was: proposed. **Gap** no tool sets a class's or library's description (`NI.Lib.Description`). **Proposed**
`lvai_set_class_description(lvclassPath, text)`: writes, reads back, saves only the `.lvclass`; refuses or
transliterates characters outside CP1252 (stored ANSI: "→" became "?" with no error). **Evidence** a harness run
2026-10-11/12 (15 classes). **Workaround** `kit/pa_set_class_description.xml`. **Removes** that helper.

## move-to-folder
**Status** shipped in 2.2 (`lvai_move_to_folder`). Was: proposed. **Gap** no tool moves a class or library member into a virtual folder. **Proposed**
`lvai_move_to_folder(lvclassPath, folder, itemNames, createFolder)`, saving only the `.lvclass`. **Evidence** a harness
run 2026-10-11/12 (every member of 15 classes). **Workaround** `kit/pa_class_folder_create_and_move.xml`,
`pa_class_folder_move.xml`. **Removes** those helpers.

## rename-member
**Status** proposed (S5); RN-1, RN-3, RN-4 settled (and the user's Q33: renames only through LabVIEW). **Gap** no rename tool; an unloaded caller keeps the old link
silently. **Proposed** `lvai_rename_member(vi, newName, lvclassPath, projectPath)`: loads every caller, renames, saves
callers and class, deletes the old file, reports per caller the new link and the string references left. **Evidence**
pilot rules 64, 85–87. **Workaround** `pa_rename_member.xml`, `pa_resave_vis.xml`, grep. **Removes** most of `ops/rename.md`.

## class-library-icons
**Status** shipped in 2.2 (`lvai_set_owner_icon`). Was: proposed (S1). **Gap** no tool sets a class or library icon; `ApplyIconToVIs` needs the project closed, does
not save members, and does nothing on a plain `.lvlib` unless members are opened. **Proposed** `lvai_set_owner_icon(owner,
png)`: Set Icon, open members, apply, save each, codes per member. **Evidence** pilot rules 26, 42, 58, 59.
**Workaround** `icon_set_class_icon`, `icon_set_library_icon`, `icon_apply_icon_and_save_n`. **Removes** `ops/icons.md`
steps 5–6.

## icon-generator
**Status** proposed (S1); KT-3 open, KT-4 settled in the audit. **Gap** icons come from a kit generator. **Proposed** a
generator reading `.labview/conventions/icon-spec.json`: own-layer, class and library PNGs, a preview. **Evidence** S1;
Q19, Q20. **Workaround** `make_icons.py`. **Removes** "generate" in `ops/icons.md`.

## icon-readback
**Status** shipped in 2.2 (`lvai_read_icons`). Was: proposed (S1); a "before" read-back (IC-4) settled. **Gap** `Save VI Icon to File` writes nothing into a
missing folder or past MAX_PATH, with no error. **Proposed** a batch read-back against expected PNGs returning pixel
differences. **Evidence** pilot rules 58, 80. **Workaround** `icon_get_vi_icons_n(_file).xml`, `icon_readback_inputs.py`,
`pixcmp.py`. **Removes** `ops/icons.md` steps 3 and 7 (the read-backs).

## set-vi-icon-keep-layers
**Status** shipped in 2.2 (`lvai_set_vi_icon` `keepOwnLayer`). Was: proposed (MC-5). **Gap** `lvai_set_vi_icon` flattens the icon. **Proposed** `keepOwnLayer: true`
(re-apply the template only). **Evidence** rule candidate 110; S16. **Workaround** skip VIs with an own layer.
**Removes** that warning.

## wire-dynamic-events-fix
**Status** shipped in 2.2 (any depth, `wireRightSide`, several user events by `dynIndex`, Use Default on the new tunnel); the AIXML element for the dynamic terminal is still open. Was: proposed (S7). **Gap** no AIXML element for the dynamic event terminal; the tool branches an authored tunnel,
wires the left side only, refuses several user events, skips its finish on the diagram route, saves the project by
default; searches two levels only (the error-case shape is three: Error 91, no change); the case tunnel it leaves has
no value in the other frames, and AIXML refuses "Use Default if Unwired". **Proposed** an AIXML element for both
sides; until then `rightSideTo: "Unregister For Events"`, several user events (`dynIndex` = position on Register),
the finish on the diagram route, no project save, the event structure found at any depth, Use Default set on the
tunnel it creates, and the property allowed in AIXML. **Evidence** pilot rules 39, 60; a harness run 2026-10.
**Workaround** `pa_wire_dyn_deep.xml`, `pa_wire_dyn_right.xml`, `set_use_default.py`, `set_user_event_specs.py`,
`pa_reg_to_control.xml`, `pa_reg_indicator.xml`, `pa_reg_through_error_frame.xml`. **Removes** `ops/helper-loop.md`
build steps 5–7c.

## user-event-cluster
**Status** proposed (S7). **Gap** an events typedef, its field and accessor take several calls. **Proposed**
`lvai_create_user_event_cluster(ctlPath, events, projectPath, bindAsField, accessors)`. **Evidence** pilot rules 66, 67.
**Workaround** create typedef, bind, accessors. **Removes** that step in `ops/helper-loop.md`.

## control-property-setters
**Status** partly shipped in 2.2 (`lvai_set_vi_descriptions`, `.vi` only); the property setters still open. Was: proposed (S7). **Gap** no tool sets mechanical action, visibility, panel-on-call flags, VI description or
reentrancy; AIXML cannot carry the first two and a convert loses the flags. **Proposed** `lvai_set_vi_properties`,
`lvai_set_control_properties` (plot names included), `lvai_set_vi_descriptions` (whole texts in a batch), verified by
a cold read; or AIXML attributes a convert keeps. **Evidence** pilot rules 40, 52, 57, 65, 81, 82; a harness run 2026-10 (61
descriptions in one call; plot names by `{LV.Plot}` `Plot Name`). **Workaround** `pa_set_mechanical_action`, `pa_switch_and_reset_boolean`, `pa_set_control_visible`,
`pa_set_panel_on_call`, `pa_read_boolean`, `pa_read_panel_on_call`, `pa_replace_description`, `set_reentrant_flags.py`,
`pa_set_vi_descriptions`, `pa_set_plot_names`.
**Removes** those helpers; the property steps in `ops/helper-loop.md`.

## generate-with-events-fixes
**Status** proposed (S7). **Gap** `lvai_generate_vi_with_events` drops the overwritten VI's panel flags; an
all-user-event structure fails without a Timeout frame. **Proposed** keep the flags; add the empty Timeout frame.
**Evidence** pilot rules 62, 65. **Workaround** re-apply flags; author the frame. **Removes** those notes.

## press-control
**Status** proposed (S7, S10). **Gap** no tool presses a button on a running VI. **Proposed** `lvai_press_control(viName,
control, value)` with `Value (Signaling)`, naming a latch as such instead of a bare 1193. **Evidence** pilot rules 25, 35.
**Workaround** `pa_press_control_signal.xml`. **Removes** the press step in `ops/run-checks.md`.

## run-vi-async
**Status** proposed (S10); partly covered: 1.8.5 `runForMs` runs N ms then aborts (no cleanup). RC-2 settled.
**Gap** no tool starts a never-returning VI and returns, stops it cleanly, or closes its panel. **Proposed**
`lvai_start_vi`, `lvai_stop_vi(closePanel)`, `lvai_run_for(viPath, ms, stopControl, readFiles)` pressing stop (not
abort) and reporting whether every started VI left memory. **Evidence** pilot rules 57, 63. **Workaround**
`pa_run_vi_async.xml`, `pa_close_panel.xml`, a project launcher. **Removes** the interactive shapes in `ops/run-checks.md`.

## read-running-vi
**Status** proposed (S10). **Gap** no tool reads a control of a running VI. **Proposed** `lvai_read_running_vi(viName,
controls)` with state and panel-open, 1004 as `notInMemory`. **Workaround** `pa_read_control(_u32).xml`. **Removes**
those helpers.

## read-named-indicators
**Status** proposed (MC-4); RC-3 (settled) relies on it. **Gap** the runner returns the whole panel (111–519 KB, one
answer over the gRPC limit); large answers of other tools go to a file. **Proposed** `readOnly: [names]`, arrays
truncated with their length, a filter for `describe_*`. **Evidence** S15; pilot rule 33. **Workaround** a wrapper VI;
`read_saved_answer.py`. **Removes** those notes.

## nets-dump
**Status** proposed. **Gap** an export hides the dynamic event terminal. **Proposed** `lvai_vi_nets(viPath)`: every wire
with typed endpoints, offline through the bundled pylabview. **Evidence** pilot rule 60; S8. **Workaround**
`vi_nets.py`. **Removes** the nets steps in `ops/review.md`.

## af-describe-actor
**Status** proposed (S8). **Gap** reviewing one actor takes 3–5 exports and a careful read. **Proposed**
`lvai_af_describe_actor(lvclassPath)`: per override Call Parent, hooks (shape, order, error wiring, class source); per
helper loop the registration route, Register's error source, frames, events created or destroyed;
`lvai_af_describe_application` adds the launch tree and qualified-name dependencies; JSON with file, VI, uid.
**Evidence** S8; pilot rules 60, 73, 74, 93. **Workaround** exports, `vi_nets.py`. **Removes** most of `ops/review.md`'s
"where to look".

## save-version-check
**Status** proposed (MC-8, X-2 settled; Q2); the scan script is ported (`<skill>/kit/lv_save_version.py`). **Gap** no tool reads or sets
a project/library Save version; saves with no project open upgrade older files. **Proposed** `lvai_set_save_version(
projectPath | libraryPath, version)`, the save version in `lvai_describe_project`, and saving tools refusing a write
newer than it. **Evidence** rule candidate 100; agent V (`work/V/save-version.md`); BA-15. **Workaround** XML line in the
closed `.lvproj`, `.lvversion`, `lv_save_version.py`. **Removes** "Save version" steps 1, 2 and 4.

## bind-fields-step-errors
**Status** proposed (MC-7). **Gap** `lvai_bind_class_fields` runs on after a failed step and names the wrong cause.
**Proposed** stop after a failed step; pick the note by its error. **Evidence** S12. **Removes** that bullet.

## plugin-agent-traps
**Status** proposed (S9). **Gap** the plugin's agents do not know the measured traps or the AF build order, and hand off
to test frameworks that may be missing. **Proposed** agents read a shipped trap list and check the framework first.
**Evidence** S9. **Workaround** briefs carry the traps. **Removes** the trap block in `session/brief.md`.

## vi-server-catalogue
**Status** partly shipped in 2.2 (Project, ProjectItem, Library classes); `BD.CleanUp`, `SetSaveVersion`, `ref{UDP}` and the validator crash still open. Was: proposed. **Gap** `lvai_vi_server_reference` lacks `BD.CleanUp` and the Project and Library classes (Save,
Close, `SetSaveVersion`), `{LV.LVClassLibrary}` `Description` and `{LV.ProjectItem}` (`AddItem`, `Move`, `Name`);
`lvai_aixml_reference` lacks `ref{UDP}`. **Proposed** add them, generated from LabVIEW's `resource\lvserver.rsc`, which
holds every name; and `lvai_validate_aixml` must answer an error, not crash, on an invented name (an invented
`{LV.Application}` method crashed LabVIEW 2026 Q3 in the validator, 2026-10). **Evidence** pilot rules 46, 51; agent
V; a harness run 2026-10. **Removes** those notes and the "never probe" warning.

## convert-target-folder
**Status** proposed; partly covered (`lvai_generate_vi`, `lvai_convert_vis_to_aixml` create it in 1.8.5). **Gap**
`lvai_convert_aixml_to_vi` and `lvai_convert_vi_to_aixml` do not create the target folder (Error 7). **Proposed** create
it. **Evidence** pilot rules 13, 75; 1.8.5 source. **Removes** those two bullets.

## generate-calls-loaded-members
**Status** possibly fixed upstream. **Gap** VIs that call class members needed placeholder stubs and swaps. **Upstream
evidence** labview-mcp 1.8.5 `docs/aixml-call-loaded-vi.md` §4, §7: a `Call` to a member opened through its project
converts, and `lvai_generate_vi` takes that route itself. Not re-run here for the AF launch calls. **Evidence** pilot
rules 8, 50. **Removes** the class-wire bullet once a run confirms it.

## placeholder-array-of-class
**Status** partly shipped in 2.2 (one stub per target, a class keeps its cluster); `array{path}` still open. Was: proposed. **Gap** `lvai_placeholder_subvi` gives a scalar `path` for an array-of-class terminal, flattens a
typedef cluster that holds a class into a scalar `path`, and gives members with the same pane ONE shared stub.
**Proposed** an `array{path}` stand-in; keep the typedef type; one stub per target name. **Evidence** pilot rule 53;
S4; a harness run 2026-10 (seven hand-made stubs). **Removes** those bullets.

## swap-subvis-fixes
**Status** partly shipped in 2.2 (constants at any depth, ambiguous labels refused, Remove Bad Wires after swap, bind and add-method); node by uid and a missing-subVI node still open. Was: proposed. **Gap** a stub shared by several nodes is swapped on an unpredictable node; a missing-subVI node
cannot be swapped and the error reads `noActiveProject`; a swap, bind or `lvai_add_class_method` can leave a broken
wire segment and answer only "state 0"; `constantsJson` finds top-level constants only (1055 for one inside a
structure). **Proposed** select the node by uid or frame path; repair or name a missing-subVI node; search
constants at any depth; run Remove Bad Wires at the end of `lvai_swap_subvis`, `lvai_bind_typedef_constants` and
`lvai_add_class_method` and report the broken-wire list. **Evidence** pilot rules 38, 72, 86; S5; a harness run 2026-10
(five rebuilds and a restart where one Remove Bad Wires fixed it). **Workaround** export after each swap
(`aixml_frames.py`); `pa_clean_member.xml`; `pa_replace_constant_deep.xml`. **Removes** those bullets.

## describe-class-ancestry
**Status** proposed. **Gap** `lvai_describe_class` lists rename history as ancestors for a class derived from LabVIEW
Object. **Proposed** the parent from `Parent Libraries` only. **Evidence** pilot rule 16. **Removes** that bullet.

## coercion-dots-blind
**Status** proposed. **Gap** `lvai_coercion_dots` reads `subViCalls: 0`; `typedefInSavedFile` passes before a bind.
**Proposed** fix both. **Evidence** pilot rule 15. **Removes** that bullet.

## project-item-tools
**Status** partly shipped in 2.2 (`lvai_create_library`; BOM and line endings kept on the tools' own edits); `.lvproj` creation and the item edits still open. Was: proposed. **Gap** project, class and library items need byte-exact edits no tool makes (drop a stray item,
move one into a folder, add a top-level VI, set scope, remove a member and its file); `lvai_create_class` adds the parent
as a top-level item; no tool creates a `.lvproj` (with virtual folders) or a plain `.lvlib`, although VI Server can
(`Project.New`, `AddItem` Folder, `Library.Create`, measured in a harness run 2026-10). **Proposed** `lvai_project_items(op, ...)`, project closed, BOM and line endings kept. **Evidence**
pilot rules 12, 34, 54, 56, 70. **Workaround** `lvproj_drop.py`, `lvproj_move.py`, `lvproj_add_toplevel.py`,
`set_scope.py`, `remove_members.py`. **Removes** those scripts and the hand-edit cautions.

## message-interface-method
**Status** proposed. **Gap** `lvai_create_message_class` refuses an interface method. **Proposed** support it (the
`Parent Libraries` block, the `Send <method>.vi` name). **Evidence** pilot rule 19. **Workaround**
`lvai_create_message_class.xml` + `repair_r1.py`. **Removes** that route.

## runner-array-inputs
**Status** proposed. **Gap** the runner cannot set arrays, refuses empty values, and lists over ~100 paths pass its size
limit. **Proposed** array, empty and file inputs. **Evidence** pilot rules 47, 58; S1, S3. **Workaround** `;`-strings,
`*_file` twins. **Removes** the list-input bullet.

## typedef-class-element-default
**Status** proposed. **Gap** `lvai_create_typedef` cannot put a class element in a cluster (`{protocol: <class>}`) and
cannot set a default value (a U32 with default 500). **Proposed** a class element by `.lvclass` path, and a `default`
per element. **Evidence** a harness run 2026-10 (two derived helpers needed). **Workaround** a derived VI Server helper per case.
**Removes** those helpers.

## clearer-answers
**Status** partly shipped in 2.2 (`missingInterfaceOverrides`, the bare subVI name resolved); `pathStandInsLeft` now documented as expected. Was: proposed. **Gap** answers that point the wrong way: `lvai_add_class_method` reports `ok:false`,
`pathStandInsLeft` for a path stand-in inside a cluster terminal that a later pane bind resolves;
`lvai_bind_typedef_constants` with a bare `subViName` answers 1055 "no active project" when the name is not qualified;
`lvai_exec_state` says "VI has an error of type 8" for a class that implements an interface without overriding one of
its methods. **Proposed** report the stand-in as pending, say "name not qualified", and name the missing override.
**Evidence** a harness run 2026-10. **Workaround** the notes in `knowledge/labview-mcp.md`. **Removes** those notes.

## Where each audit and pilot suggestion went
- S1 icons (class-library-icons, icon-generator, icon-readback, runner-array-inputs); S2 restart-with-guards,
  memory-inspection; S3 cleanup-diagram, vi-server-catalogue; S4 typed-add-class-field, remove-class-field,
  accessor-options, placeholder-array-of-class; S5 rename-member, swap-subvis-fixes; S6 create-override, add-hook,
  add-class-method-rerun; S7 wire-dynamic-events-fix, user-event-cluster, control-property-setters,
  generate-with-events-fixes, press-control, library-virtual-folder; S8 af-describe-actor, nets-dump; S9 call-lock,
  close-project-guard, dialog-detection, restart-with-guards, project-state-guard, plugin-agent-traps; S10 run-vi-async,
  read-running-vi, press-control.
- S11 deadline-abort, exec-state-batch; S12 dialog-detection, offline-loadability, bind-fields-step-errors; S13
  close-project-guard; S14 project-open-report; S15 read-named-indicators; S16 set-vi-icon-keep-layers.
- MC-1 deadline-abort; MC-2 dialog-detection, offline-loadability; MC-3 close-project-guard, project-open-report; MC-4
  read-named-indicators; MC-5 set-vi-icon-keep-layers; MC-6 add-to-class; MC-7 bind-fields-step-errors; MC-8
  save-version-check.
- KT-1 offline-loadability; KT-2, KT-8 exec-state-batch; KT-3, KT-4 icon-generator; KT-5, KT-6 restart-with-guards;
  KT-7 save-version-check, deadline-abort, dialog-detection. These are kit ports first; they shrink once a candidate ships.
- TR-1..TR-3 are AF facts (`knowledge/actor-framework.md`). TR-4 is applied as scope notes in `knowledge/labview-mcp.md`.
  TR-5 (rule candidates 100–111) is used here as evidence; they live in `knowledge/labview-mcp.md`; the pilot's own rules file stays as it is (maintenance).
