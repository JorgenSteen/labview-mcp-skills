# Clean Up Diagram on generated VIs

**When:** at the end of a step that generated or regenerated VIs (an AIXML round trip discards the layout), after the
last regeneration of those VIs; when the user asks to tidy VIs this task made. A request to clean up existing code
goes by `convention: hygiene.cleanup-diagram`.

**What it gives:** LabVIEW's Clean Up Diagram (`BD.CleanUp` + `Save.Instrument`) on each listed VI, with the proof
that only the layout changed: a code per VI, the file versions unchanged, git showing only those `.vi` files, and a
sweep that matches the one before.

**Not here:** which VIs may be cleaned and what is preferred over Clean Up Diagram (`convention:
hygiene.cleanup-diagram`; in local mode, or when the hygiene concern is off, follow the surrounding code instead);
icons (`ops/icons.md`); the sweep itself (`ops/sweep.md`).

## Before you start

- **Level:** it writes, so level 3 or 4 (`SKILL.md`). Read the project's `hygiene.md` if it exists.
- **The list:** only the VIs this task generated or regenerated, written down before step 1 (the step that made
  them knows them; `git diff --name-only <start commit>` helps, but a VI merely re-saved by another op is not on
  it). Never a folder by default.
- **The neighbours' style first, where the convention asks for it.** The toolchain has no measured route to lay out
  a diagram in a given style; how close it can get is an open measurement. Say so to the user, and run this op only
  where Clean Up Diagram is the chosen fallback.
- **Order:** generation done → this op → icons (`ops/icons.md`; the two do not affect each other) → sweep. Any later
  regeneration of a VI discards its cleanup: run this op again for it. A later swap or scripted edit on a cleaned VI needs this op again too.
- **LabVIEW is running** (`session/start.md`); no other LabVIEW agent; project **closed** (the cleanup helper runs in
  the default instance; close as `knowledge/labview-mcp.md`, "Opening and closing a project" says).
- **Commit before you start** (or record `HEAD` when the target is already committed). Git is the only undo.
- **Loadability:** if the VIs belong to a class or library this session did not build, run
  `python <skill>/kit/lv_loadability.py <owner folder>` first and stop on anything unresolved (`ops/sweep.md`,
  step 2). > MCP-candidate: offline-loadability

## Save version (this op's own variant)

The helper saves with no project open, and such a save writes the IDE's version (measured: 7 of 7 LabVIEW 2020 VIs
became 2026). General route: `knowledge/labview-mcp.md`, "Save version".
1. Scan the listed VIs: `python <skill>/kit/lv_save_version.py <vi> [...]`. Compare with `project.json`
   `save_version` (or what the project's files show).
2. **No conflict** when the IDE's version is the project's version.
3. **Conflict** when the project is older than the IDE: the cleanup save would upgrade the VIs. **Ask the user
   before the first save**, and do not choose for them. Facts to give: a `.lvversion` file over the folder, or a
   class/library Save version, may keep the old version (documented by NI, not measured here); the helper's
   `project path` input runs it in the open project's instance instead (not measured for Clean Up Diagram); or the
   cleanup is skipped for these VIs.
4. Re-scan after every batch. Any file newer than `save_version`: stop, report, restore it from git with the project
   closed. > MCP-candidate: save-version-check

## Steps

1. **Precheck.** `lvai_status`; project closed; `git status --short` recorded.
2. **BEFORE sweep** of the listed VIs: `ops/sweep.md` steps 3–9, with the `.vi` paths as arguments. Keep the report.
3. **Path lists:**
   `python <skill>/kit/sweep_paths.py <vi> [...] --no-control --from 0 --to 5 --out <scratch>/clean_0.txt`.
   - `--no-control`: the proof is step 7, so **N = the count it prints** (no "minus 1").
   - One VI needs no batching. Only `*.vi` files are listed.
4. **Helper.** `<skill>/kit/pa_cleanup_diagram_file.xml` (input `vi list`; outputs `report` = `code<TAB>path` per
   line, and `ok count`). Generate and run it as `knowledge/labview-mcp.md`, "Helper VIs (the kit)" says. **Omit**
   the `project path` input: omitted means the default instance (unless step 3 of the save-version route chose
   otherwise). Under ~100 VIs the string twin `pa_cleanup_diagram.xml` (`vi paths`, from `--json --no-control`) works.
5. **Timed first batch** of up to 5 VIs, `timeoutSeconds` passed explicitly. Measured: 0.25–0.8 s per VI on newly
   generated VIs; 4–5 s per VI on an older tree whose libraries load with each VI. Size the remaining batches so
   one call needs at most half its timeout, then run them in order.
6. **Per batch:**
   - `ok count` = the batch's N; list every line whose code is not 0.
   - Re-scan the versions (above).
   - `git status --short` shows **only the `.vi` files of this batch**. Size changes say nothing (a version
     conversion changed files by -4988 to +336 bytes). A `.lvclass`, `.lvlib`, `.ctl` or `.lvproj` change means
     something else happened: stop and report.
   - Commit the batch by explicit paths.
7. **AFTER sweep** (`ops/sweep.md`, steps 3–9) and compare with step 2: every VI has the state it had before (a VI
   broken before stays `pre-existing`, not a cleanup failure), the control reads `0 7`, membership is unchanged.
8. **Panel settings,** only for listed VIs that have a Switch When Released button, panel-on-call flags or a hidden
   control. A re-save is the moment to check them, although no change is expected.
   - Find them in the VI's AIXML source. Without a source, offline from the file: `pylv_extract` shows the execution
     flags (show front panel on call); the panel's Boolean mechanical actions are read cold with
     `<skill>/kit/pa_read_boolean.xml`.
   - Read them back after the cleanup: `pa_read_panel_on_call.xml`, `pa_read_boolean.xml` (project closed).
   - None in the list: write `panel checks: none needed`.

> MCP-candidate: cleanup-diagram (steps 3–6 become one call).

## Report

```
cleanup <n> VIs (generated by <step>)  start HEAD <hash>  batches <n> (<N1> + <N2> ...)  <s> s per VI
codes: <ok>/<N> code 0   not 0: <path> <code> | none
versions: before <v> after <v>  (conflict: <asked: answer> | none)   git: only .vi of each batch yes/no
sweep before/after: <same | changed: path state>   control 0 7   membership unchanged yes/no
panel checks: <result | none needed>   commits <hashes>   LabVIEW calls <n>   issues: <exact text | none>
```
Every re-saved file, and any version change, also goes into the end-of-session side effects (`session/close.md`).

## Traps

- `BD.CleanUp` is missing from `lvai_vi_server_reference` (`knowledge/labview-mcp.md`,
  "lvai_vi_server_reference, lvai_aixml_reference");
  it exists: `{LV.VI}` Invoke `BD.CleanUp`.
- On a hand-laid diagram Clean Up Diagram can make things worse: a template's Actor Core grew from 1160x495 to
  1290x925, its straight error and class rails were broken, and the arrows of its scripting comments crossed other
  code. This is why the convention limits it to generated VIs.
- This helper accepts a trailing `;` in its list; the icon apply helper does not.
