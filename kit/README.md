# kit/: scripts and helper VIs of the labview skill

The kit holds what the skill's `ops/` and `session/` files run beside labview-mcp's own tools:

- **Helper VIs** as AIXML (`*.xml`): VI Server scripting that no labview-mcp tool does yet (the AF hook shapes the
  tools refuse or lack, Clean Up Diagram, front-panel properties, sweeps, reads of running VIs).
- **Python scripts** (standard library only): byte-exact edits of `.lvproj`/`.lvclass`/`.lvlib` files, input lists
  for the helpers, offline reads of VI files (links, nets, versions, loadability), icon generation and read-back.
- **PowerShell scripts**: LabVIEW's close, dialogs, CPU time over a span and the Nigel chat, with no LabVIEW call
  (the window list itself is `lvai_labview_state`).
- **Examples** (`example_*.xml`): measured AIXML bodies to copy from.

**How helpers are used** (generate into the helper folder, run with `lvai_run_vi_and_read_values`, input rules,
when to regenerate, save in a separate call): `knowledge/labview-mcp.md`, "Helper VIs (the kit)". Which project state
each helper needs: the same file, "Project open or closed, per kind of call". Each `.xml` names its inputs and
outputs as control labels, and its `description` attribute says what it does; the table below is the index.

Scripts print their usage with no arguments, and most have a `--check`/`-Check` dry run or self-test. Paths passed to
LabVIEW are absolute and long-form (no `%TEMP%`, no 8.3 names). A row's **MCP candidate** is the id in
`MCP-CANDIDATES.md` whose labview-mcp tool would replace the file. "Used by" names the skill files that cite the file
today; "(planned)" marks a file whose route file is not written yet.

The project's own files (`project.json`, `checks.json`, `decisions.md`) start from `conventions/templates/`. The pilot
kit's `project.example.json` is superseded by `conventions/templates/project.json` and is not in the kit.

## Files

### Session, process and offline checks

| File | Kind | What it does | Used by | MCP candidate |
|---|---|---|---|---|
| `lv_start_nigel_chat.ps1` | powershell | Starts the Nigel chat (`LVNigelChat.exe --lv-version --lv-bitness`), so the labview-mcp service comes up; never kills. `-Check` prints the command only. | session/start.md | ensure-labview-complete, restart-with-guards |
| `lv_press_ok.ps1` | powershell | Presses OK on a message box of one given PID (a box our own probe raised); refuses a LabVIEW PID. `-Check` lists the boxes. | session/start.md | restart-with-guards |
| `lv_close.ps1` | powershell | Closes the one LabVIEW (`CloseMainWindow` + wait), prints the timing and `CloseMainWindow`'s answer (False = close message not taken: busy or modal; True + timeout = a dialog came up); never kills. Only with the user's go-ahead. `-Check` dry run. | session/restart.md | restart-with-guards |
| `wait_lv_idle.ps1` | powershell | Samples LabVIEW's CPU time per window (default 30 s) until it is idle for N windows, logging visible window titles; `-Once` for one sample. Read-only; `-Check`. | session/restart.md | deadline-abort |
| `lv_dialog.ps1` | powershell | Names the dialog that blocks LabVIEW (title, buttons, text). `-Escape` cancels it with Esc, **only with the user's go-ahead** for that dialog; refuses several matches or a dialog not in front. | session/restart.md (planned) | dialog-detection |
| `lv_loadability.py` | python | Offline load closure per VI/class/library/project/folder: "loadable", or the unresolved dependencies grouped by package with the load chain; `--lazy`, `--json`, `--links`, `--check`. Exit 1 = something does not resolve. | ops/analysis.md, sweep.md, class-field.md, cleanup.md, icons.md, rename.md, review.md, run-checks.md | offline-loadability |
| `lv_save_version.py` | python | The LabVIEW version a `.vi`/`.ctl`/`.vim` (version stamps, a heuristic) or a `.lvclass`/`.lvlib`/`.lvproj` (`LVVersion`, `NI.LV.All.SaveVersion`) was saved in, on disk or at a git revision. `--check`. | knowledge/labview-mcp.md "Save version"; ops/analysis.md, cleanup.md, icons.md; session/brief.md, close.md | save-version-check |
| `read_saved_answer.py` | python | Compact read of a tool answer saved to a file because it was too large (`describe_project`, `placeholder_subvi`, `add_class_method`). Read-only. | ops/analysis.md, run-checks.md, sweep.md; session/restart.md; knowledge/labview-mcp.md | read-named-indicators |
| `check_error_outputs.py` | python | Lists the error outputs a helper's AIXML leaves unwired (`error out:`), file or folder; each one raises LabVIEW's automatic error dialog when it errors on a VI with automatic error handling on. Exit 1 when any; `--quiet` counts only; `--check` self-test. Read-only. | knowledge/labview-mcp.md "Helper VIs (the kit)" | helper-auto-error |
| `pa_auto_error_off.xml` | helper XML | Writes `{LV.VI}` `Automatic Error Handling` = F on one VI (`vi path`), saves it, reads it back (`automatic error handling`, `error out`); every error output wired. Run on each generated helper before its first run (always on the grpc backend). Project closed. Measured 2026-10-26: off = no dialog, on = the modal dialog. | knowledge/labview-mcp.md "Helper VIs (the kit)" | helper-auto-error |

### Sweep, cleanup, membership, nets

| File | Kind | What it does | Used by | MCP candidate |
|---|---|---|---|---|
| `sweep_paths.py` | python | Builds the `;`-separated VI list (with a missing-path negative control) for the sweep, cleanup and re-save helpers, or the list file of their `*_file` twins; `--from/--to` batches. | ops/sweep.md, cleanup.md, analysis.md, class-field.md | exec-state-batch, runner-array-inputs |
| `pa_exec_state_sweep.xml`, `pa_exec_state_sweep_file.xml` | helper XML | `Execution:State` and error code per VI path in one call (list string, or a list file from ~100 VIs up). Project closed. | ops/sweep.md | exec-state-batch |
| `check_membership.py` | python | Every `.vi` in a folder with a `.lvclass` (else `.lvlib`) must be an item of it; prints `MISSING` lines. Read-only. | ops/sweep.md, analysis.md, class-field.md, rename.md, review.md | exec-state-batch, add-class-method-rerun |
| `pa_cleanup_diagram.xml`, `pa_cleanup_diagram_file.xml` | helper XML | Clean Up Diagram + save per VI path (list string or list file); `project path` omitted = project closed. | ops/cleanup.md | cleanup-diagram |
| `pa_resave_vis.xml` | helper XML | Re-saves each listed VI (no cleanup), e.g. after a private-data change or a rename. | ops/class-field.md, rename.md | remove-class-field, rename-member |
| `vi_nets.py` | python | Every wire of a block diagram as typed endpoints, offline through labview-mcp's bundled pylabview; shows the dynamic event terminal an export hides. Read-only. | ops/review.md, analysis.md, class-field.md, run-checks.md | nets-dump, af-describe-actor |
| `aixml_frames.py` | python | Each `<Call>`/`<Node>` of an AIXML export with its enclosing structures and Case frames (which frame a swap landed in). Read-only. | ops/analysis.md; knowledge/labview-mcp.md | swap-subvis-fixes |

### AF overrides, hooks, messages, libraries

| File | Kind | What it does | Used by | MCP candidate |
|---|---|---|---|---|
| `af_add_hook_call_node.xml` | helper XML | A hook fed from a node's terminal, any terminal (e.g. a release hook's `error out` into a log VI); `lvai_af_add_hook` `branchFromNode` taps only a series hook's class output. | ops/override.md | add-hook |
| `pa_insert_series_branch.xml` | helper XML | In-series hook in front of ONE far terminal (`far name A/B`, owner class `far owner class`, default `CallParentNode`), every other branch of the wire kept on the panel terminal. Saves the VI only (then `pa_save_member`). Project open and active. | ops/override.md | add-hook |
| `pa_insert_series2.xml` | helper XML | In-series hook on one or two NAMED panel wires (block A, block B); after Call Parent the roles swap (`hook in` = the side facing the indicator). The route for the measured third wire on Handle Error (`stop actor?` and `error out`), which `lvai_af_add_hook` cannot wire; reconnects ONE far end only. Project open and active; then `pa_save_member`. | ops/override.md (E-after) | add-hook |
| `pa_reg_to_control.xml` | helper XML | In a helper-loop VI, replaces the top-level Register For Events by an input control carrying the same registration refnum (Create Control on Register's input, delete Register, its Unbundle and the fresh constant, wire the control to the loop tunnel), assigns it to pane slot `term index`, saves. No Remove Bad Wires (on purpose). Project open and active. | ops/helper-loop.md (step 7b) | wire-dynamic-events-fix |
| `pa_reg_through_error_frame.xml` | helper XML | In a helper-loop VI after step 7b: wires the registration refnum through the event loop's Error frame (case input tunnel to case output tunnel), so Unregister gets the live refnum on an error exit; all lookups first, `apply` F = dry run. `variant` 1 only: variant 2 (Unregister from the control) is the measured failure that hangs every stop. Project closed. | ops/helper-loop.md (step 7c) | wire-dynamic-events-fix |
| `pa_reg_indicator.xml` | helper XML | In a VI with one Register For Events whose refnum output is unwired (an actor's `init`): Create Indicator on that output, assign it to pane slot `term index`, save. Project open and active. | ops/helper-loop.md (step 11) | wire-dynamic-events-fix |
| `pa_wire_nodes.xml` | helper XML | On a VI's top-level diagram, wires a terminal of one subVI node to a terminal of another (nodes by VI-name regex, terminals by name) and reads the wire back (ends, broken). Does not save: `pa_save_member` next. Project open and active. | ops/helper-loop.md (step 11) | add-hook |
| `pa_insert_seq_hook.xml`, `pa_append_seq_hook.xml` | helper XML | A one-frame Flat Sequence after Call Parent holding a hook; a second hook in the same frame after the first. | ops/override.md | add-hook |
| `pa_close_join.xml` | helper XML | Wires the close shape in an Actor Core: finds Call Parent, the helper-loop node and the frame's stop hook by VI-name regex (`vi path`, `class path`, `close vi path`, `loop vi regex`, `stop vi regex`; optional `remove vi regex`, `class terminal name`, `merge style` 2147, `indicator label`), creates the close subVI and two Merge Errors: Merge(loop, stop hook) -> close; Merge(Call Parent, close) -> `error out`; Call Parent's error out stays an order tunnel into the frame. The optional delete is outside the error chain (1055 in `delete node error` = nothing matched); hook error inputs `error in` or `error in (no error)`. Project open and active, one run, then `pa_save_member`. | knowledge/labview-mcp.md; ops/override.md | add-hook |
| `pa_remove_series_block.xml` | helper XML | Takes one wire pair of a series subVI node out and bridges it: every lookup first, then deletes the in- and out-wire (and the node when `delete node` T), wires the source to every kept branch and far end, reads the wire back, saves the VI (then `pa_save_member`). Run once per pair. Project open and active. | ops/override.md (section 5); knowledge/labview-mcp.md | add-hook |
| `pa_clean_member.xml` | helper XML | Remove Bad Wires + save of a member. | ops/sweep.md; knowledge/labview-mcp.md | add-hook |
| `pa_save_member.xml` | helper XML | Saves a member edited in memory plus its class, in a separate call. | knowledge/labview-mcp.md | add-hook |
| `pa_frame_hook_sink.xml` | helper XML | In an override with one one-frame Flat Sequence: finds a subVI node INSIDE the frame by VI-name regex and wires one of its terminals into a new subVI dropped in the same frame (an appended hook's `error out` into `Clear Errors`, input `error in (no error)`). `apply` F = dry run; saves the VI and the class. Project open and active. | ops/override.md | add-hook |
| `repair_r1.py` | python | Repairs an interface message from the Message Maker helper (`Parent Libraries` block, `Send <method>.vi` name), byte-exact; project closed. | knowledge/labview-mcp.md | message-interface-method |
| `pa_stop_actor_from_panel.xml` | helper XML | Sends Normal Stop to a running actor tree whose enqueuer you do not hold (reads the actor object from a running hook's panel); needs a socket VI edited to your actor type. | ops/run-checks.md (planned) | run-vi-async |

### Classes, fields, renames, project items

| File | Kind | What it does | Used by | MCP candidate |
|---|---|---|---|---|
| `pa_array_element_replace.xml` | helper XML | Turns a typedef `array{bool}` into an array of a class (or `.ctl`) element, for an array-of-class field. Project open and active. | ops/class-field.md; knowledge/labview-mcp.md | typed-add-class-field |
| `pa_ctl_delete_fields.xml` | helper XML | Deletes up to two fields of a `.ctl` cluster by label (the middle step of removing a class field). | ops/class-field.md | remove-class-field |
| `pa_rename_member.xml` | helper XML | Renames a member through Save As with its caller and class loaded; the old file stays on disk. | ops/rename.md; knowledge/labview-mcp.md | rename-member |
| `set_scope.py` | python | Sets member scope in a `.lvclass` (both scope properties), byte-exact; project closed. | ops/class-field.md; knowledge/labview-mcp.md | project-item-tools, add-class-method-rerun |
| `remove_members.py` | python | Removes member `<Item>` blocks from a `.lvclass`/`.lvlib` at any depth, optionally deletes their files; byte-exact; project closed. | ops/class-field.md; knowledge/labview-mcp.md | project-item-tools, remove-class-field |
| `lvproj_drop.py` | python | Removes `.lvproj` item lines containing a substring, byte-exact (BOM and CRLF or LF kept); writes nothing on no match or when the substring hits a structural line. Project closed. | ops/class-field.md; knowledge/labview-mcp.md | project-item-tools |
| `lvproj_move.py` | python | Moves a one-line `.lvproj` item into a sibling virtual folder (`--create` makes it); byte-exact; project closed. | knowledge/labview-mcp.md | project-item-tools |
| `lvproj_add_toplevel.py` | python | Adds one-line VI items directly under My Computer; refuses a name or URL already listed; byte-exact. | knowledge/labview-mcp.md | project-item-tools |
| `pa_new_project.xml` | helper XML | Creates and saves a new `.lvproj` with virtual folders under My Computer (`new lvproj path`, `folder names` `;`-separated). No project needs to be open. | knowledge/labview-mcp.md | project-item-tools |
| `pa_project_add_file.xml` | helper XML | Adds one existing file directly under My Computer (`{LV.TargetItem}` `AddFile`); the close saves the project. Project open and active. | knowledge/labview-mcp.md | project-item-tools |
| `make_batch_json.py` | python | Builds `methodsJson` for `lvai_add_class_method` or `editsJson` for `lvai_swap_subvis` from a CSV/JSON table; warns on a shared stub. Read-only. | ops/helper-loop.md; ops/class-field.md (planned) | - |
| `make_probe.py` | python | Copies an AIXML under a throwaway VI name, so a first trial convert cannot burn the real name. | knowledge/labview-mcp.md | - |
| `patch_ctl.py` | python | Turns a generated VI bundle into a typedef `.ctl` (flag patch). | knowledge/labview-mcp.md | - |

### Helper loops, front-panel properties, runs

| File | Kind | What it does | Used by | MCP candidate |
|---|---|---|---|---|
| `set_use_default.py` | python | Sets "Use Default if Unwired" (objFlags +0x200000) on case output tunnels left unwired in a frame, in a `pylv_extract` bundle; `--check` lists them. Touches every such tunnel. | ops/helper-loop.md; knowledge/labview-mcp.md | wire-dynamic-events-fix |
| `set_user_event_specs.py` | python | Writes user-event specs with an explicit `dynIndex` into a `pylv_extract` bundle before `pylv_rebuild`. | knowledge/labview-mcp.md; ops/helper-loop.md | wire-dynamic-events-fix |
| `set_reentrant_flags.py` | python | Sets shared-clone reentrancy on a `pylv_extract` bundle (a static hook inside a dispatch recursion). | knowledge/labview-mcp.md | control-property-setters |
| `pa_set_mechanical_action.xml`, `pa_switch_and_reset_boolean.xml` | helper XML | Mechanical action of a Boolean (project closed); or the same plus a reset local in its Value Change frame (project open and active). | ops/helper-loop.md (`pa_set_mechanical_action`); knowledge/labview-mcp.md (`pa_switch_and_reset_boolean`) | control-property-setters |
| `pa_set_control_visible.xml` | helper XML | Shows or hides a control (e.g. the local-variable `stop`), read back, saved. Project closed. | ops/helper-loop.md | control-property-setters |
| `pa_set_panel_on_call.xml`, `pa_read_panel_on_call.xml` | helper XML | Writes / reads cold "show front panel on call" and "close after call" (+ state). | `pa_set_panel_on_call`: knowledge/labview-mcp.md, ops/helper-loop.md; `pa_read_panel_on_call`: ops/cleanup.md, ops/helper-loop.md | control-property-setters |
| `pa_read_boolean.xml` | helper XML | Cold read of a Boolean's mechanical action and visibility; read-only. | ops/cleanup.md; knowledge/labview-mcp.md | control-property-setters |
| `pa_replace_description.xml` | helper XML | Search-and-replace in a VI description, read back, saved. Project closed. | ops/rename.md; knowledge/labview-mcp.md | control-property-setters |
| `pa_set_vi_descriptions.xml` | helper XML | Writes WHOLE VI descriptions from a record file (`record list`: absolute VI path TAB new text, records separated by LF), reads each back, `Save.Instrument`; one report line per VI, `ok count`. Icons and state kept (61 VIs in one call). Project closed. | knowledge/labview-mcp.md | control-property-setters |
| `pa_replace_constant_deep.xml` | helper XML | Replaces a diagram constant found by label up to three levels down with a class constant (`{LV.Constant}` Replace), saves; `lvai_swap_subvis` `constantsJson` finds top-level constants only. Project open and active. | knowledge/labview-mcp.md | swap-subvis-fixes |
| `pa_wire_by_label.xml` | helper XML | Wires terminal `source name` of the node labelled `source label` to terminal `sink name` of the node labelled `sink label` (top level; works for primitives, e.g. `Create Folder`); `apply` F = dry run (counts, every label), T = wire and save when both counts are 1. Project closed. | knowledge/labview-mcp.md | add-hook |
| `pa_save_orphan.xml` | helper XML | Saves a path-less VI by name (`VI Name`, `Save Path`) in the active project's instance, so the project can close after a convert failed at save (Error 1019). Project open and active. | knowledge/labview-mcp.md | close-project-guard |
| `pa_set_plot_names.xml` | helper XML | Sets the names of plot 0 and plot 1 of a waveform chart found by label (`{LV.WaveformChart}` `Active Plot` / `Plot`, `{LV.Plot}` `Plot Name`), reads back, saves. Two plots only. Project closed. | knowledge/labview-mcp.md | control-property-setters |
| `mem_lines.py` | python | Prints the lines of a saved `pa_project_vis_modified` answer (too large for a tool result on a big project): every line to a file, the modified ones and filter hits to the screen. | knowledge/labview-mcp.md | memory-inspection |
| `pa_save_libraries.xml` | helper XML | Per library: `Library.Open`, `Save All This Library.vi`, only modified. The only save for a modified `.ctl` (`Open VI Reference` answers 1035 for one). Project open and active. | knowledge/labview-mcp.md | add-to-class |
| `pa_project_vis_modified.xml` | helper XML | Every VI/ctl in memory in the ACTIVE PROJECT's instance with its modification bitsets; `save modified?` T saves the modified ones. The answer can exceed the tool-result limit on a large project. | knowledge/labview-mcp.md | memory-inspection |
| `pa_run_vi_async.xml` | helper XML | Starts a never-returning VI (Run VI, Wait Until Done F) without blocking the service. | ops/run-checks.md; knowledge/labview-mcp.md | run-vi-async |
| `pa_close_panel.xml` | helper XML | Closes a VI's front panel so a stopped top-level VI leaves memory. | ops/run-checks.md; knowledge/labview-mcp.md | run-vi-async |
| `pa_press_control_signal.xml` | helper XML | Writes `Value (Signaling)` to a control of a running VI (an event structure sees it); a latched Boolean refuses (1193). | ops/run-checks.md; knowledge/labview-mcp.md | press-control |
| `pa_press_control.xml` | helper XML | `Ctrl Val.Set` on a Boolean of a running VI (no Value Change event): the older form of the above. | - | press-control |
| `pa_read_control.xml`, `pa_read_control_u32.xml` | helper XML | Reads a String / U32 control of a running VI, plus its state and panel-open; 1004 = not in memory. | ops/run-checks.md; knowledge/labview-mcp.md | read-running-vi |
| `PA-log.xml` | helper XML | A user.lib logging VI (one time-stamped line per call). Edit its `log path` constant first (it holds a placeholder path), generate it into `<LabVIEW>\user.lib\LV_MCP\`, then Call it by bare name; writing into the LabVIEW install needs the user's go-ahead. | - | - |

### Icons

| File | Kind | What it does | Used by | MCP candidate |
|---|---|---|---|---|
| `make_icons.py` | python | 32x32 icon generator from `.labview/conventions/icon-spec.json`: VI composites, own layers, class templates, library icons, manifest, preview; `--check` writes nothing. | ops/icons.md | icon-generator |
| `icon-spec.example.json` | example | A small generic spec for `make_icons.py`; `_doc` explains every key. Copy to `.labview/conventions/icon-spec.json`. | ops/icons.md | icon-generator |

### Examples

| File | Kind | What it does | Used by | MCP candidate |
|---|---|---|---|---|
| `example_helper_loop.xml` | example | Helper loop with notifier exit. | ops/helper-loop.md | - |
| `example_pli_body_obtain_notifier.xml`, `example_pli_deferred_start.xml` | example | Pre Launch Init bodies: obtain a notifier; deferred start. The deferred-start body is the older branch form (class in only): for the measured form after Call Parent add `<C> out` and wire its error out (`ops/override.md`, section 2). | ops/override.md (deferred start; obtain notifier planned) | - |
| `example_sc_body_fire_notifier.xml` | example | Stop Core body that fires the notifier. | ops/override.md (planned) | - |
| `example_launch_nested.xml` | example | A launch method for a nested actor. | ops/override.md (planned) | - |
| `example_interface_override_forward.xml` | example | Interface override forwarding to the caller. | ops/override.md (planned) | - |
| `example_launcher_ui_stop.xml` | example | Headless launcher that presses the UI's Stop. | ops/run-checks.md (planned) | - |
| `example_launcher_last_ack.xml` | example | Actor stop proof: N launches with a proof-owned queue, Normal Stop, the Last Ack's code per launch, a second stop (1556). The two top-level path stand-ins become the actor class and `Last Ack.lvclass` (validate refuses them as they are: convert with `validateFirst: false`, then `constantsJson`). | ops/run-checks.md | - |
| `example_ctl_defaults.xml` | example | Sets and reads back a standalone typedef's default value (project closed); retype `wanted` and `type template` to your typedef. | ops/class-field.md | - |
| `example_to_json.xml`, `example_notifier_typedef.xml` | example | A to_json method; a notifier typedef. | ops/helper-loop.md (planned) | - |

The examples use the pilot's `PA-` names and `LVMCP Stub …` names: replace the stub names with the ones
`lvai_placeholder_subvi` returns for your VIs, and edit the cluster stand-ins to match your class's fields.

## Kit TODO

- **make_icons.py, IC-3 / IC-7 / KT-4 (settled):** not implemented yet. It still draws white 3x5 banner text and a
  library glyph under the banner. Needed: a black Small Fonts banner (RT style, 3x5 white only on request), one
  `class_glyph` per class on the right of the body (the class template = banner + class glyph), `lib_glyph`
  optional (a library needs only a banner), `libraries`/`messages: keep|generate`, and `--only <list file>` so only
  new or regenerated VIs are drawn. `icon-spec.example.json` changes with it.
- **KT-2, check_membership.py:** find the owner by walking up to the nearest `.lvclass`/`.lvlib` (not only the VI's
  own folder); `--allow <file>` for project-level items by design; `--before <report>` for new MISSING lines only.
- **KT-3, make_icons.py:** take the owner from the `.lvclass`/`.lvlib` file found in the VI's folder or above, the
  folder name only as a fallback with a warning (75 of 437 classes in the audit's reference code differ).
- **KT-6, lv_close.ps1:** the message half is done (it prints `CloseMainWindow`'s answer and tells busy from a late
  dialog, RS-5); separate exit codes for the two cases (1 vs 3) are still open.
- **KT-8, sweep helper:** an `owner list` input that holds each owning library open for the batch (a library then
  loads once, not once per VI), and `sweep_paths.py --ext .vi,.vim,.ctl`.
- **wait_lv_idle.ps1 and lv_dialog.ps1 (KT-7):** ported and run read-only against an idle LabVIEW; `lv_dialog.ps1
  -Escape` has not been run since the port (it needs a live dialog and the user's go-ahead).
- **Pilot text in copied files:** `lv_start_nigel_chat.ps1` and the Python headers still cite the
  pilot's skill names and rule numbers as provenance; `PA-log.xml` holds a placeholder log path in its constant.

## Retired (a labview-mcp tool does the job now)

Removed on 2026-10-26, when labview-mcp 2.2 shipped the tools below. Nothing was lost: every file is in commit
`539094c` (`git show 539094c:kit/<file> > <file>` brings one back), and its measured facts are in the tool's own
description or in labview-mcp's `docs/`. Kept on purpose because a tool does not cover it: `af_add_hook_call_node.xml`
(a node's error output into a log VI), `pa_insert_series2.xml` (a series insert on any named panel wire, e.g. Handle
Error's `stop actor?`; restored the same day), `pa_insert_series_branch.xml` (a series insert on a wire with branches, which
`lvai_af_add_hook` refuses), `pa_remove_series_block.xml` (what `lvai_af_remove_hook` refuses as
`seriesHookNotRemovable`), `pa_save_member.xml` and `pa_clean_member.xml` (after the kept hook helpers),
`pa_project_vis_modified.xml` (it can SAVE the modified VIs; `lvai_vis_in_memory` only reads), `pa_set_vi_descriptions.xml`
(a typedef's description; the tool takes `.vi` only), `set_user_event_specs.py` and `set_use_default.py` (the offline
check of what `lvai_wire_dynamic_events` wrote, and a hand fix), `lv_dialog.ps1`, `lv_close.ps1`, `lv_press_ok.ps1`,
`lv_start_nigel_chat.ps1` and `wait_lv_idle.ps1` (no official tool closes LabVIEW, answers a dialog or samples CPU
over a span).

| File | Replaced by | Note |
|---|---|---|
| `lvai_create_override.xml` | `lvai_create_override` | same helper ships in labview-mcp's `scripts\` |
| `lvai_create_actor_library.xml` | labview-mcp `<scriptsDirectory>\lvai_create_actor_library.xml` | byte-identical; `lvai_status` reports `scriptsDirectory` |
| `lvai_create_message_class.xml` | labview-mcp `<scriptsDirectory>\lvai_create_message_class.xml` | byte-identical; still the route for an interface message, then `repair_r1.py` |
| `icon_set_class_icon.xml` | `lvai_set_owner_icon` | ported as `lvai_icon_set_class_icon.xml` |
| `icon_set_library_icon.xml` | `lvai_set_owner_icon` | ported as `lvai_icon_set_library_icon.xml` |
| `icon_apply_icon_and_save_n.xml` | `lvai_set_owner_icon` `applyToMembers` | ported as `lvai_icon_apply_and_save_n.xml` |
| `icon_apply_icon_and_save.xml` | `lvai_set_owner_icon` | the four-VI predecessor |
| `icon_apply_icon_to_vis.xml` | - | negative control of the 2026-10 measurement (ApplyIconToVIs saves nothing) |
| `icon_carrier.xml` | `lvai_set_owner_icon`, `lvai_read_icons` | ported as `lvai_icon_carrier.xml` |
| `icon_get_class_icon.xml` | `lvai_read_icons` | ported as `lvai_icon_get_class_icon.xml` |
| `icon_get_library_icon.xml` | `lvai_read_icons` | ported as `lvai_icon_get_library_icon.xml` |
| `icon_get_vi_icon.xml` | `lvai_read_icons` |  |
| `icon_get_vi_icons_n.xml` | `lvai_read_icons` |  |
| `icon_get_vi_icons_n_file.xml` | `lvai_read_icons` | ported as `lvai_icon_get_vi_icons_n_file.xml` (100 VIs per call) |
| `icon_readback_inputs.py` | `lvai_read_icons` | it creates the folders and refuses long paths itself |
| `pixcmp.py` | `lvai_read_icons` `expectedDir` | the compare is a port of this script |
| `pa_set_class_description.xml` | `lvai_set_class_description` | also refuses text outside CP1252 |
| `pa_class_folder_add_files.xml` | `lvai_add_to_class` | creates the folder; relinks and saves the callers you list |
| `pa_class_folder_add_existing.xml` | `lvai_add_to_class` | adds into an existing folder |
| `pa_class_folder_move.xml` | `lvai_move_to_folder` |  |
| `pa_class_folder_create_and_move.xml` | `lvai_move_to_folder` `createFolder` |  |
| `pa_new_library.xml` | `lvai_create_library` | also lists it in the project, sets the description, adds items |
| `pa_vis_in_memory.xml` | `lvai_vis_in_memory` | reads every instance, not only the default one |
| `pa_vis_modified.xml` | `lvai_vis_in_memory` | ported as `lvai_vis_modified.xml` |
| `lv_windows.ps1` | `lvai_labview_state` | adds a screenshot per possible dialog and hidden-window checks |
| `af_add_hook_call.xml` | `lvai_af_add_hook` `branch` | `af_add_hook_call_node.xml` stays: it wires any node output |
| `pa_delete_subvi.xml` | `lvai_af_remove_hook` | deletes ONE node by name and bypasses a series hook; the kit helper deleted every node with a terminal |
| `pa_wire_dyn_deep.xml` | `lvai_wire_dynamic_events` | any depth, both sides, Use Default on the new tunnel |
| `pa_wire_dyn_right.xml` | `lvai_wire_dynamic_events` `wireRightSide` |  |
