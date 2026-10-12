# Run the checks: test VIs and behaviour runs from checks.json

**When:** after an edit to a class that has a round-trip test (`convention: hygiene.test-after-edit`); after a build
or a change; at a session start or end; when the user asks to "run the tests", "run the checks", "does it still
work".

**What it gives:** one line per entry of `.labview/checks.json`. A test VI passes on its named `Pass` Boolean and
`error out` (`convention: hygiene.test-convention`); a behaviour run passes on the readings its entry expects. The
readings go into one evidence file per session.

**Not here:** whether every VI is runnable (`ops/sweep.md`); writing tests (labview-mcp's test agents, below). In
local mode, or when the hygiene concern is off, run what `checks.json` lists and judge each entry by what it names.

## Before you start

- **It runs code,** with whatever side effects the code has; each entry states them (`side_effects`). Any level.
- **`checks.json`** (template `<skill>/conventions/templates/checks.json`). None yet: offer to create it from the
  template with the tests the user names; write it only on a yes.
- **Which entries:** after a class edit, only the entries whose `class_under_test` is that class; otherwise every
  entry, or those the user names.
- **LabVIEW is running** (`session/start.md`); no other LabVIEW agent; the project state as each entry says
  (default closed: a test VI run cold loads only what it calls). Close or open as `knowledge/labview-mcp.md`,
  "Opening and closing a project" says.

## Entry format

`{ "$schema_version": 1, "tests": [ ... ], "runs": [ ... ] }`. Paths are relative to the repo root, so several
source trees are fine; make them absolute and long-form before any call.

**`tests[]`**

| Key | Meaning |
|---|---|
| `name`, `path` | the test's name; the test VI (or the runner or test class, see `kind`) |
| `kind` | `vi` (default), `caraya` (`path` = a Caraya suite runner VI) or `lunit` (`path` = the `.lvclass`/`.lvlib` of the tests) |
| `class_under_test` | the class whose edits trigger this test (`hygiene.test-after-edit`) |
| `project` | `closed`, or the `.lvproj` to open first (tests often live in a test project, not the development one) |
| `inputs` | control label → value as text; `{}` = the defaults |
| `expected` | `pass`: the Pass Boolean's label (default `Pass`); `error out code`: 0, or `"none"` for an old test without `error out`; other named values with their rule. A project whose tests use another summary indicator (e.g. `ALL GOOD?`) names it in `pass`. |
| `read_only` | the indicators to read when the panel is large (step 3) |
| `returns` | `true` once step 2 has shown the VI returns by itself; `false` = run it as a run |
| `timeout_s`, `side_effects`, `evidence` | the call's budget; what the run changes (files, hardware); where the readings go |

**`runs[]`:** `name`, `path`, `project`, `preconditions`, `steps` (ordered: a tool or kit helper and its inputs),
`inputs`, `expected`, `timeout_s`, `repeat` (default 1), `during` (another run that must be running), `evidence`.

## Steps

1. **Preconditions.** `lvai_status` (version, up seconds); `git status --short` recorded; the output files a run
   reads noted (a run that clears them first says so).
2. **Before the first run of a test VI** (once; again when the VI changes):
   - **Loadability:** `python <skill>/kit/lv_loadability.py <test vi>`. Unresolved: `NOT RUN: not loadable:
     <packages>`; never load it (a missing package raises a modal dialog that blocks the service).
     > MCP-candidate: offline-loadability
   - **Does it return?** `python <skill>/kit/vi_nets.py <test vi>` on the VI and its project subVIs (offline). A While
     loop whose stop is not reachable without a panel press means a synchronous run would block the service: set
     `returns: false` and run it as a run (step 4). Otherwise `returns: true`.
3. **Test VIs** (`tests[]`), in list order, one call at a time:
   - **`kind: vi`:** `lvai_run_vi_and_read_values` with `viPath`, `inputsJson` = `inputs` (omit it for `{}`),
     `timeoutSeconds` = `timeout_s`, `includeRawXml` false.
   - **Pass** = the named Pass Boolean reads true **and** `values["error out"]` has code 0. Other indicators are
     informational; Booleans inside arrays or clusters never count. A missing Pass Boolean, or a missing
     `error out` the entry does not mark `"none"`, is a `FAIL` naming what is missing. `errorCode` and
     `helperErrorCode` are the runner's, not the test's.
   - **Large panels:** an answer over the size limit (`ResourceExhausted`) means the VI ran but nothing came back:
     report `NOT READABLE`, not a fail of the code. To read it, a wrapper VI that calls the test and returns only
     `Pass` and `error out` is needed; it is new code, so ask first and put it in the test library. An answer saved
     to a file is read with `<skill>/kit/read_saved_answer.py`, never by running again.
     > MCP-candidate: read-named-indicators
   - **`kind: caraya`:** `lvai_run_caraya_tests` with `runnerViPath`. The verdict is its `ok` and the failing cases
     it names, never the runner's `error out`.
   - **`kind: lunit`:** `lvai_run_lunit_tests` with the narrowest `testPath` (the `.lvclass`). `tests` must be above 0
     (`foundNoTests` means nothing ran); then `allPassed` and `failures`.
4. **Behaviour runs** (`runs[]`), in list order, `repeat` times; a run named in `during` happens between the start
   and the stop of its host run.
   1. Check the preconditions, e.g. nothing of the tree is running: a cold `lvai_exec_state` of the loop VI reads 1.
   2. Do the `steps` exactly. Typical shapes:
      - **Headless run:** a launcher VI that runs N ms itself and returns readings (`lvai_run_vi_and_read_values`):
        line counts, the last line, error lines. **Error run:** the same with the input that forces the failure;
        expect the error line and text, and no data lines.
      - **Interactive run:** start the never-returning VI with `<skill>/kit/pa_run_vi_async.xml` (it cannot set
        controls: the VI runs with its defaults); read the running loop VI with `pa_read_control.xml` /
        `pa_read_control_u32.xml` (state 3, panel open); press its stop with `pa_press_control_signal.xml`
        (`Value (Signaling)`; a latched Boolean answers 1193); confirm the output stopped and the loop VIs left
        memory (1004); close a panel that was opened with `pa_close_panel.xml`.
      - `runForMs` (with `signalsJson`) on `lvai_run_vi_and_read_values` gives a snapshot of a never-ending VI, then
        **aborts** it with no cleanup: use it only for VIs that hold no hardware and no files, never as stop proof.
   3. Compare with `expected`. A time outside `timeout_s` is a fail, reported with the time measured.
   4. Afterwards a cold `lvai_exec_state` of the main loop VIs reads 1 (nothing left running). Something still
      running: the entry's rescue step if it has one; otherwise stop and report. A hung loop may need a restart,
      which is the user's decision (`session/restart.md`).
   > MCP-candidate: run-vi-async, press-control, read-running-vi
5. **Evidence.** One file per session at the entries' `evidence` path (e.g. `<proof_folder>/runs/<id>-checks.txt`):
   date, LabVIEW and labview-mcp versions, project state, then one block per entry with the exact readings, and
   copies of output files beside it (`<id>-<run><n>-<what>.txt` per repeat). For a repo without git, outside the
   product tree (`conventions/dot-labview.md`, "No git").
6. **Git.** `git status --short`: only the evidence files are new. A file under `source_root` that a run re-saved is
   a side effect: report it, do not commit it blindly. Commit the evidence by explicit paths (`convention:
   hygiene.commit-messages`).

## Writing tests: labview-mcp's agents

Tests are written by the plugin's `labview-caraya-unit-test` agent (the default) or `labview-lunit-unit-test` (only
when the user asks for LUnit). Brief them (`session/brief.md`) with: what to test, the target folder, the `.lvproj`,
and the rules `convention: hygiene.test-convention` (a round-trip test for a class that packs or bundles data;
outputs `Pass` and `error out`), `hygiene.test-library` (which library) and the naming rules for the test files.
Afterwards check that the test reports a Boolean named `Pass` plus `error out`, sits in the test library, and add
its entry to `checks.json` (`kind: caraya` for a generated runner, or `vi` for a test VI). Both agents run the code
under test.

## Report

```
checks <all | class <name> | named>  tests <p>/<n> pass  runs <p>/<n> pass  project <state>  calls <n>  <min> min
<name>  PASS | FAIL | NOT RUN | NOT READABLE  Pass=<T/F>  error <code>  <named values>   (per test and repeat)
failures: <exact values, error text, missing Pass or error out>
evidence <file>   commit <hash>   git <clean | leftovers>   side effects <files re-saved | none>
```

## Traps

- **A test chains `error in` through every node with a side effect.** An unwired `error in` beside a parallel call
  races: a second `Create Folder` that ran before the first one's `init` made a test fail once and pass on the
  rerun (a harness run, 2026-10).
- **A private VI cannot be run top-level** (error 1390): a forced-error run of a private member needs a public
  wrapper, or a test inside the class (a harness run, 2026-10).

- `lvai_run_vi_as_top_level` blocks on a VI that never returns; on a launcher it may answer an error code although
  the tree started. Confirm by reading the running loop VI, not the code.
- A test VI may write into an output file a run also reads (a shared log): run error runs after the test VIs, or let
  the launcher clear its files first.
- Line counts depend on timing: expect a range (e.g. 8–11 lines for 5 s at 500 ms), never one number. Compare JSON
  after parsing (timestamps change), never as a whole string.
- A stopped top-level VI whose panel was opened stays in memory and reads state 1, not 1004, until its panel closes.
- `pa_read_control` answering error 1 ("not found") together with state 3 still proves the VI is in memory and runs.
- An off-pane control keeps its value only while the VI stays in memory: two separate tool runs unload it in between,
  so a reset test calls the VI twice from one caller (`knowledge/actor-framework.md`).
