# Review an AF design or built actors

**When:** "review the design", "check this actor", "is the application consistent", before a build, or after one as
its final check. Read-only, offline first.

**What it gives:** two kinds of rows, each with evidence (file, VI, node or wire, or a doc section and line):
- **knowledge rows:** a hazard from `knowledge/actor-framework.md` found in the code (a hang, a leak, a broken VI).
  They hold in every project, with or without conventions.
- **convention rows:** "deviates from this project's conventions", one row per `convention:` id that the code does
  not follow. A concern marked `status: off` gets no rows. **Local mode:** no convention files are read; the code is
  compared only with the surrounding area (its neighbours in the same tree or subsystem).
A finding without evidence is not a finding.

**Not here:** fixing anything (the fix column names the op); execState (`ops/sweep.md`); behaviour
(`ops/run-checks.md`); gathering a project's conventions (`ops/analysis.md`).

## Before you start

- **Setup level:** 1 for a few actors, 2 for a whole tree (offer at the end to keep what was learned, `SKILL.md`).
- **Inputs:** `.labview/conventions/*.md` (the rule text; never restated here), `.labview/decisions.md` and
  `.labview/analysis/` (the areas and their observed shapes). No decisions and no analysis on an existing project:
  ask the user once which choices were deliberate, and record their words and the date in the report. Code built
  under the project's conventions in an earlier session counts as new code for severity (evaluation 2026-10).
- **Mode:** design (requirements, architecture and diagram docs; no LabVIEW) or build (the files).
- `git status --short` before; it must be identical after. Scratch output (nets, exports) goes to `<repo>/mcp_temp/`,
  which git ignores.

## Steps

1. **Areas.** Split the scope into areas (deployable trees, subsystems) from `analysis/` or the folder layout.
   Every comparison and the consistency check run per area (`convention: af-shapes.one-pattern-per-area`).
2. **Inventory**, offline: per actor its class, parent, library, members by virtual folder, overrides, helper loops,
   events typedef, messages, launch sites. From the `.lvclass`/`.lvlib` XML and
   `python <skill>/kit/check_membership.py <folder>`. On code the review did not build, a MISSING line is a note (a
   dead file, or a launcher kept as a project item), not a stop.
3. **Nets first.** `python <skill>/kit/vi_nets.py <vi> --work <scratch>` answers every override, hook and loop
   wiring row with no LabVIEW call (a whole application of 1411 VIs took about 55 min, audit F); it also shows the
   dynamic event terminal an export hides. Only what nets do not carry needs an export (frame names, Timeout values,
   panes, properties): `lvai_convert_vi_to_aixml` into a scratch folder, project closed, after
   `python <skill>/kit/lv_loadability.py` says the VI loads. An AIXML source beside a VI may be older than the VI.
   Constants (paths, Timeout values, typedef defaults) are not in `vi_nets` dumps: read them from an AIXML export
   and check its date against the VI's; an older one is unverified. `vi_nets` cannot see Conditional Disable
   structures either: `hygiene.conditional-disable` needs an export. (evaluation 2026-10)
   `lv_loadability.py` needs `--vilib` on a station with several LabVIEW installs; its `--links` on a `.lvlib`
   prints only the path (links are listed for VIs). (evaluation 2026-10)
   > MCP-candidate: nets-dump > MCP-candidate: af-describe-actor
4. **Concern table:** one row per concern (helper loop, stop, close/destroy, events, errors, launch, messaging), one
   column per actor, each cell the shape found with its evidence. It feeds the consistency rows.
5. **Knowledge rows**, then **convention rows** (tables below).
6. **Classify** each row: severity, recorded deviation (a `decisions.md` entry or an open item names it), fix column.
7. `git status --short` unchanged.

## Knowledge rows (hazards; `knowledge/actor-framework.md`)

| hazard | where to look | finding |
|---|---|---|
| a Destroy that can run before the stop is generated or before the loop exits | Stop Core, Actor Core after Call Parent, `close`, the loop VI (nets) | Destroy in Stop Core while the stop is sent after Call Parent; Destroy in the loop VI. Generate-then-Destroy both in Stop Core is not this hazard |
| the stop's Generate chained on Call Parent's error | Actor Core nets: Generate's `error in` source | skipped exactly when Call Parent failed |
| a loop whose only exit is an event, with Register skippable by an upstream error | `init` nets (or, in older code, the loop VI's): Register's `error in` (no incoming error in the convention); the error case inside the loop | the loop can start unregistered and wait for ever |
| a teardown hook in Actor Core's stop frame (D-append) that needs the helper loop to have exited | Actor Core: what runs in the D frame vs inside `close` | it runs before the loop exits: wrong order, two writers at once (measured) |
| Register For Events inside the loop VI (not in an `init` before Call Parent) | Actor Core nets: what runs before Call Parent; loop VI: a Register node | a Call Parent that returns at once lets the stop come before the registration: the tree hangs (measured, `knowledge/actor-framework.md`) |
| a launch in Pre Launch Init | PLI nets: Launch Root/Nested Actor | hangs |
| private dynamic-dispatch member; static VI inside a dynamic recursion cycle | `.lvclass` scope; dispatch from `lvai_describe_class` or the pane (the `.lvclass` has no `IsStaticMethod` property, evaluation 2026-10) | broken VI |
| a handler before Call Parent that is meant to keep the actor running | Handle Error nets | the parent still returns `stop actor?` = T |
| side work chained on Handle Error's `error in` | Handle Error nets | skipped at every normal stop (error 43) |
| 0 ms Timeout with non-blocking work | event structure Timeout value (export) | busy loop |
| a child's library referencing its caller | link info of the child's files (read by `kit/lv_loadability.py`), not a raw grep, which hits cached types | dependency cycle |

## Convention rows (cite the id; read the rule in `.labview/conventions/`)

| convention ids | where to look |
|---|---|
| `af-shapes.helper-loop-vi`, `.helper-loop-error-case`, `.registration`, `.stop-mechanism` | Actor Core: `init` before Call Parent, its refnum into the loop VI; `init` nets: Register; loop VI nets: the refnum control, the error case (the refnum wired through its Error frame, no use-default tunnel feeding Unregister), the dynamic terminal, Unregister (fed from the loop's output tunnel, never from the control; its error not hidden by the Merge order), locals, the `stop` call after each non-event loop |
| `af-shapes.stop-site`, `.close-vi`, `.resources` | Actor Core after Call Parent, `close`, Stop Core, PLI |
| `af-shapes.events-typedef`, `.global-events`, `.prelaunch-settings` | private data (decoded), TypeDefs, accessors, PLI |
| `af-shapes.handle-error-order`, `.handle-last-ack`, `.hook-vis` | Handle Error, HLAC, hook panes (hooks may take `stop actor?`, `Last Ack`) |
| `af-shapes.timed-work` | event structure frames and Timeout values |
| `af-shapes.launch-owner`, `.dependency-direction`, `.tree-shape`, `.shutdown-cascade` | launch sites, link info, the launch tree |
| `af-shapes.base-actor`, `.messages` | class hierarchy (template copies in a family are a note), Messages folders, Drop Message Core |
| `errors.default-policy`, `.plan-required`, `.no-plan-statement`, `.loop-errors`, `.ignored-errors`, `.release-errors`, `.launcher-error-out`, `.custom-error-codes`, `.placeholder-error`, `.not-handled-yet`, `.log-local` | Handle Error, loop VI error outs, `NI.Lib.Description` in the `.lvclass` XML, Stop Core hooks (unwired `error out` vs Clear Errors) |
| `naming.*` | file names per class folder, private data labels |
| `layout.*` | `.lvlib` per actor, virtual folders, typedef owners, scopes, accessors present vs used |
| `hygiene.descriptions`, `.conditional-disable`, `.test-convention` | `NI.Lib.Description`; Conditional Disable structures and their bookmark comment; the test library |
| `af-shapes.one-pattern-per-area` | the concern table, per area |

**Consistency** (`one-pattern-per-area`): a concern solved two ways inside one area, with no decision, is a row
against the odd one out. Two areas with different shapes are reported as "area A: shape X; area B: shape Y" (note).
New code inside an existing area is compared with that area's shape (the local pattern wins for a small change).

**PLI failure cleanup and Stop Core order** (DR-6, settled 2026-10-09): compare against `convention:
af-shapes.pli-failure-cleanup` and `af-shapes.stop-core-order`. On new code, a PLI that creates resources but does not
release them on its own error is a finding (Stop Core will not run); release before Stop Core's Call Parent is a note.
On existing code both are notes.

## Severity and the fix column

- **blocker (new code):** a knowledge-row hazard: a hang, a leak, a broken VI, a child depending on its caller; also a
  keep-running error handler without a written plan, and no Call Parent.
- **should (new code):** a convention row; an unwired `error out` (one ignored on purpose ends in Clear Errors).
- **note:** a single-caller leaf's direct `Send` up; template copies; a missing "no plan" statement; and **every**
  row on existing code that differs from the conventions, unless it is a knowledge hazard (then: blocker, report only).
- **fix column:** names the op (`ops/override.md`, `ops/helper-loop.md`, `ops/class-field.md`, `ops/rename.md`,
  `ops/icons.md`, `ops/cleanup.md`) only for new code or code the task changes anyway. For an area the task does not
  touch it reads **"report only"** (maintenance rule, `SKILL.md`).
- A row with a `decisions.md` entry or an open item is an **accepted deviation**. A shape written in an architecture
  doc without a decision is not accepted.
- A row the files cannot answer is **unverified**, with what would settle it (an export, a run).

## Report

```
AF review <design|build> <scope>   areas <list>   conventions <full|local|none>, concerns off: <list>
decisions read <file | none, asked the user>   LabVIEW calls <n> (exports only)   git: unchanged | changed <files>
concerns: <concern>: <shape> (<actors>) | ...
rows:
kind | id or hazard | place (file, VI, node/wire) | evidence | severity | new/existing | fix (op | report only)
accepted deviations: <id> <place> <decision>     PLI failure cleanup: <pass | finding | note> <place>
unverified: <row> <what would settle it>
```

## Traps

- `Actor out` of Actor Core's Call Parent is typed `Actor`: a cast after it is not a wiring error.
- Stop Core runs inside Actor Core's Call Parent, before anything after it: judge release order with that in mind.
- User events created in PLI are fine even when the launcher exits at once; not a lifetime finding.
- A raw grep of a `.vi` hits inherited help text and cached typedef owners: use link info or qualified names, and
  confirm with nets (115 false hits in one audit).
- pylabview cannot read every VI (14 of 1411 in the audit): list them as unverified.
- The class description is in the XML (`NI.Lib.Description`): readable offline, not unverified. VI descriptions are
  readable offline too, from the pylabview extraction `vi_nets.py` leaves in its work folder (evaluation 2026-10).
