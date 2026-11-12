# Diagram layout on generated VIs: labview-mcp's layout or NI's Clean Up Diagram

**When:** at the end of a step that generated or regenerated VIs (an AIXML round trip discards the layout; a kit
helper that later wires or inserts nodes in them lays out nothing), after the last change to those VIs; when the
user asks to tidy VIs this task made. A request to clean up existing code goes by `convention:
hygiene.cleanup-diagram`.

**What it gives:** the layout engine the project chose (`convention: hygiene.cleanup-diagram`) on each listed VI,
with the proof that only the layout changed: a code per VI, the file versions unchanged, git showing only those `.vi`
files, and a sweep that matches the one before. Both engines stay available:
- **`labview-mcp`:** `lvai_layout_diagrams`, labview-mcp's own layout. A diagram too dense or tangled for it is
  handed to NI's Clean Up by the tool itself (`layoutEngine` per VI says which one was saved). Steps 3A–4A.
- **`ni`:** LabVIEW's Clean Up Diagram (`BD.CleanUp` + `Save.Instrument`) on every listed VI, through the kit
  helper. It replaces labview-mcp's layout. Steps 3–5.

**Not here:** which VIs may be cleaned and what is preferred over Clean Up Diagram (`convention:
hygiene.cleanup-diagram`; in local mode, or when the hygiene concern is off, follow the surrounding code instead);
icons (`ops/icons.md`); the sweep itself (`ops/sweep.md`).

## Before you start

- **Level:** it writes, so level 3 or 4 (`SKILL.md`). Read the project's `hygiene.md` if it exists.
- **The list:** only the VIs this task generated or regenerated, written down before step 1 (the step that made
  them knows them; `git diff --name-only <start commit>` helps, but a VI merely re-saved by another op is not on
  it). Never a folder by default. Overrides edited by script (not generated) are on it only when the user asks.
  With engine `labview-mcp`, a VI already has that layout when a generating tool wrote it with its `cleanUpDiagram`
  step (`lvai_generate_vi(s)`, `lvai_add_class_method`, `lvai_swap_subvis`, the event and test generators; the
  answer names the step). List the rest: VIs written by `lvai_convert_aixml_to_vi`, `pylv_rebuild` or `pylv_apply`
  (no layout step), generated with `cleanUpDiagram: false`, changed by a kit helper or a script afterwards, a DQMH
  `Main.vi` (the step skips it), and those whose step answered `restored` (the raw VI). A step slimmed on success
  (`{"step": "cleanUpDiagram", "slimmed": true}`) cannot show `restored`: when it is unclear, list the VI; a second
  pass of labview-mcp's layout costs only time. With `ni`, list every VI this task generated or regenerated.
- **The neighbours' style first, where the convention asks for it.** The toolchain has no measured route to lay out
  a diagram in a given style; how close it can get is an open measurement. Say so to the user, and run this op only
  where the convention's engine is the chosen fallback.
- **Order:** generation done → this op → icons (`ops/icons.md`; the two do not affect each other) → sweep. Any later
  regeneration of a VI discards its cleanup: run this op again for it. A later swap or scripted edit on a cleaned VI needs this op again too.
- **LabVIEW is running** (`session/start.md`); no other LabVIEW agent; project **closed** (both engines save with no
  project open; the cleanup helper runs in the default instance; close as `knowledge/labview-mcp.md`, "Opening and closing a project" says).
- **Commit before you start** (or record `HEAD` when the target is already committed). Git is the only undo.
- **Loadability:** if the VIs belong to a class or library this session did not build, run
  `python <skill>/kit/lv_loadability.py <owner folder>` first and stop on anything unresolved (`ops/sweep.md`,
  step 2). > MCP-candidate: offline-loadability

## Save version (this op's own variant)

Both engines save with no project open, and such a save writes the IDE's version (measured for the helper: 7 of 7
LabVIEW 2020 VIs became 2026; not measured for `lvai_layout_diagrams`, so scan the same way). General route: `knowledge/labview-mcp.md`, "Save version".
1. Scan the listed VIs: `python <skill>/kit/lv_save_version.py <vi> [...]`. Compare with `project.json`
   `save_version` (or what the project's files show).
2. **No conflict** when the IDE's version is the project's version.
3. **Conflict** when the project is older than the IDE: the cleanup save would upgrade the VIs. **Ask the user
   before the first save**, and do not choose for them. Facts to give: a `.lvversion` file over the folder, or a
   class/library Save version, may keep the old version (documented by NI, not measured here); with engine `ni`, the
   helper's `project path` input runs it in the open project's instance instead (not measured for Clean Up
   Diagram); or the cleanup is skipped for these VIs.
4. Re-scan after every batch. Any file newer than `save_version`: stop, report, restore it from git with the project
   closed. > MCP-candidate: save-version-check

## Steps

1. **Precheck.** LabVIEW answers (`grpc`: `lvai_status`; `pylabview`: `lvai_ensure_labview` answers `ready`, it starts
   nothing while one runs, and `lvai_status` answers `ok: false` there by design); one LabVIEW only
   (`lvai_labview_state`); project closed; `git status --short` recorded.
2. **BEFORE sweep** of the listed VIs: `ops/sweep.md` steps 3–9, with the `.vi` paths as arguments. Keep the report.
3. **Engine `ni`: path lists:**
   `python <skill>/kit/sweep_paths.py <vi> [...] --no-control --from 0 --to 5 --out <scratch>/clean_0.txt`.
   - `--no-control`: the proof is step 7, so **N = the count it prints** (no "minus 1").
   - One VI needs no batching. Only `*.vi` files are listed.
4. **Engine `ni`: helper.** `<skill>/kit/pa_cleanup_diagram_file.xml` (input `vi list`; outputs `report` = `code<TAB>path` per
   line, and `ok count`). Generate and run it as `knowledge/labview-mcp.md`, "Helper VIs (the kit)" says. **Omit**
   the `project path` input: omitted means the default instance (unless step 3 of the save-version route chose
   otherwise). Under ~100 VIs the string twin `pa_cleanup_diagram.xml` (`vi paths`, from `--json --no-control`) works.
5. **Engine `ni`: timed first batch** of up to 5 VIs, `timeoutSeconds` passed explicitly. Measured: 0.25–0.8 s per VI on newly
   generated VIs; 4–5 s per VI on an older tree whose libraries load with each VI. Size the remaining batches so
   one call needs at most half its timeout, then run them in order.

**Engine `labview-mcp`, instead of steps 3-5:**

3A. **Layout:** `lvai_layout_diagrams` with `viPaths` = the list, one absolute path per line (never a folder: a
    folder takes every `.vi` under it, hand-laid ones included) and `timeoutSeconds` passed explicitly. A first call
    with up to 5 VIs, step 6 for them, then the rest in one call. `parallel` workers run on `pylabview` only.
4A. **Read its answer,** one row per VI: a failed VI is named with its `errorKind` and the others go on (list it;
    no blind retry). `layoutEngine` (`lvai_layout_diagram` or `LabVIEW Clean Up Diagram`) and `tangledFallback` per
    VI go into the report. Structure kinds it does not lay out yet (sequences, timed loops, in-place, disable) move
    whole and are named in the answer: report them. The tool keeps a backup per VI under
    `%TEMP%\LabVIEWMCP\layout\` (no knob to move it into `mcp_temp/`): name it in the side effects. Git is still the undo.

**Both engines:**

6. **Per batch:**
   - `ok count` = the batch's N (engine `labview-mcp`: the answer's totals); list every line whose code is not 0
     (every failed row).
   - Re-scan the versions (above).
   - `git status --short` shows **only the `.vi` files of this batch**. Size changes say nothing (a version
     conversion changed files by -4988 to +336 bytes). A `.lvclass`, `.lvlib`, `.ctl` or `.lvproj` change means
     something else happened: stop and report.
   - Commit the batch by explicit paths. The message says what the batch did, not that it is proven: step 7 proves it.
7. **AFTER sweep** (`ops/sweep.md`, steps 3–9) and compare with step 2: every VI has the state it had before (a VI
   broken before stays `pre-existing`, not a cleanup failure), the control reads `0 7`, membership is unchanged. A VI
   whose state changed: restore it from the start commit with the project closed (`git checkout <start HEAD> --
   <path>`), commit the restore, and report it as a cleanup failure.
8. **Panel settings,** only for listed VIs that have a Switch When Released button, panel-on-call flags or a hidden
   control. A re-save is the moment to check them, although no change is expected.
   - Find them in the VI's AIXML source. Without a source, offline from the file: `pylv_extract` shows the execution
     flags (show front panel on call); the panel's Boolean mechanical actions are read cold with
     `<skill>/kit/pa_read_boolean.xml`.
   - Read them back after the cleanup: `pa_read_panel_on_call.xml`, `pa_read_boolean.xml` (project closed).
   - None in the list: write `panel checks: none needed`.

> MCP-candidate: cleanup-diagram (engine `ni`: steps 3–6 become one call).

## Report

```
cleanup <n> VIs (generated by <step>)  engine <labview-mcp | ni>  start HEAD <hash>  batches <n> (<N1> + <N2> ...)  <s> s per VI
codes: <ok>/<N> code 0   not 0: <path> <code> | none   (engine labview-mcp: laidOut <n>, failed <path errorKind | none>)
labview-mcp: layoutEngine ours <n> / NI <n>  tangledFallback <list | none>  moved whole <list | none>   (engine ni: n/a)
versions: before <v> after <v>  (conflict: <asked: answer> | none)   git: only .vi of each batch yes/no
sweep before/after: <same | changed: path state>   control 0 7   membership unchanged yes/no
panel checks: <result | none needed>   commits <hashes>   LabVIEW calls <n>   issues: <exact text | none>
```
Every re-saved file, and any version change, also goes into the end-of-session side effects (`session/close.md`).

## Traps

- `BD.CleanUp` is missing from `lvai_vi_server_reference` (`knowledge/labview-mcp.md`,
  "lvai_vi_server_reference, lvai_aixml_reference");
  it exists: `{LV.VI}` Invoke `BD.CleanUp`.
- On a hand-laid diagram either engine can make things worse (measured for NI's Clean Up): a template's Actor Core grew from 1160x495 to
  1290x925, its straight error and class rails were broken, and the arrows of its scripting comments crossed other
  code. This is why the convention limits it to generated VIs.
- This helper accepts a trailing `;` in its list; the icon apply helper does not.
