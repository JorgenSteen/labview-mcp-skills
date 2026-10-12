# Cold sweep: every VI runnable, membership consistent

**When:** after a structural step (class, field, member, override, hook, regeneration, rename, cleanup, icons), on
the folders that step touched; before a change to code this session did not build (the BEFORE baseline); when the
user asks to "sweep", "check all VIs", "cold check".

**What it gives:** the execution state of every VI in scope, read with no project open ("cold"), proved real by a
negative control, and the file-side membership of every VI that sits beside a `.lvclass`/`.lvlib`. Both are compared
with a BEFORE run, so damage done by this task is told apart from what was broken already. `ok: true` from a writing
tool is no evidence; this is (`knowledge/labview-mcp.md`, "Evidence, git, build order").

**Not here:** whether the code does what it should (`ops/run-checks.md`); repairs (the op that made the change). The
sweep reads only and applies no convention, so it runs the same in local mode and with conventions.

## Before you start

- **Level:** a read at any level. It needs no `.labview/`; `project.json` gives `source_root`, the project files and
  `proof_folder` when they exist.
- **LabVIEW is running** (`session/start.md`) and no other LabVIEW agent is working.
- **Scope:** the folders the task touched, or the folders the user names. A whole tree only on request, and then
  only its loadable folders (step 2). Measured: one 300-VI call on a tree that does not resolve kept LabVIEW busy
  for ~2.5 h.
- **Project closed.** With a project open, good VIs read state 0. Close it as `knowledge/labview-mcp.md`, "Opening
  and closing a project" says. This op's variant: in a repo with several projects no project owns the swept
  folders, so close the one that is **active**, whichever it is (the window list from `<skill>/kit/lv_windows.ps1`
  shows it). If it or its VIs carry unsaved changes this session did not make (`*` in a title, `LVAutoSave` files),
  ask first (`SKILL.md`, "Save what you made; ask about the rest"). What the close rewrites is a side effect.

## Steps

1. **Precheck.** `lvai_status`: note `serverVersion` and `labviewUpSeconds`. Close the active project (above).
   Record `git status --short` (without git: the manifest, `conventions/dot-labview.md`, "No git").
2. **Loadability** (on code this session did not build): `python <skill>/kit/lv_loadability.py <folders>`, offline,
   seconds. Sweep only folders whose VIs all resolve. List the others as `not loadable: <folder>: <missing
   packages>` and do not load them: a missing package raises a modal "Find the VI" dialog that blocks every call.
   On a PC with several LabVIEW versions pass `--vilib` for the project's LabVIEW. > MCP-candidate: offline-loadability
3. **Path lists.**
   `python <skill>/kit/sweep_paths.py <folder or .vi> [...] --from 0 --to 10 --out <scratch>/sweep_0.txt`.
   - It lists every `*.vi` sorted (members stay grouped by library when their files are flat), plus one missing
     path, the negative control, as the last entry of each list. **N = the printed count minus 1.**
   - `--from`/`--to` index the sorted list from 0, `--to` excluded, `--to` left out = the rest. Write the later
     lists after step 5 has sized them.
   - Use absolute, long-form paths for `<scratch>`; the list file's path is the helper's input.
4. **Helper.** `<skill>/kit/pa_exec_state_sweep_file.xml` (input `vi list` = the list file; outputs `report` and
   `ok count`). Generate and run it as `knowledge/labview-mcp.md`, "Helper VIs (the kit)" says; a cached copy is
   current when its answer carries both outputs. Under ~100 VIs the string twin `pa_exec_state_sweep.xml` with
   `sweep_paths.py --json` also works.
5. **Timed first batch.** `lvai_run_vi_and_read_values` on the helper with `inputsJson`
   `{"vi list": "<sweep_0.txt>"}` and `timeoutSeconds` passed explicitly (300). Divide the call's time by N.
   - Measured rates: 51–97 ms per VI on loadable code (85 VIs in 6.4 s); ~0.23 s per VI on the pilot's generated
     tree; over 1 s and up to ~30 s per VI where a hierarchy does not resolve, because each VI reloads its whole
     library.
   - Size the remaining batches so one call needs at most half its timeout: `batch = timeoutSeconds / 2 / s-per-VI`,
     and at most ~150 VIs (a 150-VI answer is ~30 KB and still comes back inline). Run them in order, one call each.
6. **A batch passes its deadline** (`DeadlineExceeded`): follow `knowledge/labview-mcp.md`, "A failed, hung or
   blocked call: stop and report". This op's variant:
   - Record `stopped at batch <i>: DeadlineExceeded after <s> s`. That batch has no result.
   - Never send it again, smaller or with a larger budget, while LabVIEW is busy: the load would start over.
   - Once `lvai_status` answers again, report and ask the user whether to go on with the remaining batches and
     whether to split the stuck folder out. > MCP-candidate: deadline-abort
7. **Read each batch.**
   - `ok count` = the batch's N (the control is not counted).
   - The control, the last `report` line, reads `0 7`. Anything else means the helper did not really open files:
     the whole batch is invalid.
   - List every line that is not state 1 with its state and code. An answer saved to a file because it is too large
     is read with `<skill>/kit/read_saved_answer.py`, never by running the call again.
8. **Compare with the baseline.**
   - The first sweep of a folder before a change is its BEFORE baseline: keep the reports in `proof_folder` (or the
     scratch folder) as `<id>-sweep-before-<i>.txt`.
   - After the change, per path: state 1 before and after = fine; 1 before, not 1 after = **failure of this task**;
     not 1 before and after = **pre-existing** (reported; on code the task does not touch it is not fixed, `SKILL.md`,
     "Scope (maintenance)"); a VI the task added = must read 1.
   - **A VI that was not runnable and that the task edited** is fine when it ends no worse than it started: the same
     state and the same code as in the BEFORE run. Report it as **pre-existing, edited**. A different code means the
     edit changed what is wrong with it: report it as **changed** (it may be better or worse; say which if the error
     text shows it). The task does not have to make it runnable unless that is the task.
   - On a tree this session built from nothing there is no baseline: every VI must read 1.
9. **Membership.** `python <skill>/kit/check_membership.py <folder>` per swept folder. Read its exit code directly:
   a pipe into `head`/`tail` hides it.
   - On code this session built: `not a member 0`, exit 0. Every `MISSING` line is a failure.
   - On foreign code: run it with the BEFORE sweep too and compare. A `MISSING` line that was there before (an
     orphan VI, a launcher kept as a project item by design, a loose VI beside a typedef library) is reported as
     pre-existing; a new one is a failure. Never stop the sweep on a pre-existing line.
   - Limit: a VI in a sub-folder of its library (e.g. `subVI\` below the `.lvlib`) is counted `plain` and not
     checked, because the script looks for an owner in the VI's own folder only (KT-2).
     > MCP-candidate: exec-state-batch
10. **Postcheck.** `git status --short` equals step 1, apart from what the project close rewrote (a side effect).
    The sweep saves nothing: any other change is reported, never reverted.

## What a cold sweep does not cover

- Only `*.vi` files are state-checked. `.vim`, `.ctl`, `.lvclass` and `.lvlib` are not.
- No project means no target: Conditional Disable symbols defined on a project target are not in effect. On code
  whose variants come from such symbols, the cold state is not the state of a shipped variant. There is no measured
  route to sweep inside a project target yet; report such VIs as `cold only`. > MCP-candidate: exec-state-target

## Report

```
cold sweep <folders>  labview-mcp <version>  LabVIEW up <s> s  baseline <file | none: new code>
not loadable: <folder: packages> | none
batch <i>  <n> VIs  <ok>/<n> state 1  control <state> <code>  <s> s       (one line per batch)
stopped at batch <i>: <reason>                                           (only if it stopped)
not state 1: <path> <state> <code> <new | pre-existing | pre-existing, edited | changed>   (or: none)
membership: checked <n>  not a member <m> (<new> new, <pre> pre-existing)  plain <p>
git: unchanged | changed: <files>   side effects: <project closed: what it rewrote> | none
LabVIEW calls <n>   sweep calls <s> s in total
```

## Traps

- State 0 with code 0 and every dependency resolved is a real broken VI (seen on foreign code: a VI broken before
  any change). Only the baseline tells it from damage done by the task.
- State 0 "VI has an error of type 1000088" beside a freshly edited override can be a loose wire end in a **sibling**
  override of the same class (`knowledge/labview-mcp.md`, "LabVIEW scripting quirks"; repair with
  `pa_clean_member.xml` on the sibling, in the op that made the edit).
- State 0 with a broken-wire text (`<terminal> @ <node> | ...`) after a generate, swap or bind: run
  `pa_clean_member.xml` before any rebuild (`knowledge/labview-mcp.md`, "LabVIEW scripting quirks", "Remove bad wires
  first").
- A single `lvai_exec_state` answering -1 means the reference never opened: read `code` and `source`, it is no
  verdict about the VI.
- After a LabVIEW restart, a class-level call may behave differently from the old instance (a class icon set, say).
  The sweep itself does not depend on that.
