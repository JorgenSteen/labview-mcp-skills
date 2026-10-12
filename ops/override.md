# AF overrides: create one and place hook VIs in it

**When:** a task overrides an Actor Framework method of an actor class (Pre Launch Init, Actor Core, Stop Core,
Handle Error, Handle Last Ack Core), or a parent method of a plain class; hooks a member VI into an override (before,
beside or after Call Parent); or changes or removes a method an override calls.

**What it gives:** the override as a protected, dynamic member with Call Parent, its hook VIs where the shape puts
them, every member executable cold, and a run that shows the hooks in the expected order.

**Not here:** building the helper-loop VI and the order of its hooks on Actor Core (`ops/helper-loop.md`, which uses
shapes A, D and D-close below); how AF calls the overrides and their panes (`knowledge/actor-framework.md`); interface
overrides, which are ordinary `lvai_add_class_method` members with the same name and pane (pilot rule 9). In local
mode, or when a concern is off, follow the surrounding code instead.

## Before you start

- **Setup level:** a new override on a new actor is level 4 (af-shapes, naming, layout, errors). A hook added to an
  existing override in that override's own pattern is level 3. Conventions used: `af-shapes.hook-vis`,
  `af-shapes.resources`, `af-shapes.stop-core-order`, `af-shapes.pli-failure-cleanup`, `af-shapes.stop-site`,
  `af-shapes.close-vi`, `af-shapes.handle-error-order`, `af-shapes.handle-last-ack`, `af-shapes.launch-owner`,
  `af-shapes.prelaunch-settings`, `naming.override-names`, `layout.class-folders`, `errors.ignored-errors`,
  `errors.release-errors`, `errors.plan-required`, `errors.no-plan-statement`.
- **Maintenance scope.** On an existing actor, its overrides keep their shapes (Stop Core order, Handle Error order,
  teardown) unless the task is to change them. Touch only the override and the hooks the task names.
- **Hook VIs exist first.** Each hook is a class member before it is hooked, with the panes `af-shapes.hook-vis`
  allows. Overrides come last in the build order (`knowledge/labview-mcp.md`, "Evidence, git, build order").
- **Project state:** every helper here needs the project open and active; `lvai_exec_state` and the byte-exact
  scripts need it closed (`knowledge/labview-mcp.md`, "Project open or closed, per kind of call").
- **Helpers:** generate and run them as `knowledge/labview-mcp.md`, "Helper VIs (the kit)" says. Every error output of
  a helper must read 0. The inputs below are the helpers' control labels.
- **Commits:** one before and one after each override and each hook. Keep the commit right after step 1 (the bare
  override): it is the restore point for "Change a hooked method". Save version and loadability on code this session
  did not build: `knowledge/labview-mcp.md`, "Save version" and "A failed, hung or blocked call".

## 1. Create the override

`<skill>/kit/lvai_create_override.xml`, project open and active. > MCP-candidate: create-override

| input | value |
|---|---|
| `class path` | the class's `.lvclass` |
| `parent method path` | `<LabVIEW>\vi.lib\ActorFramework\Actor\<method>.vi`; for a plain class, the parent's own `.vi` |
| `new vi path` | `<class folder>\<the parent's file name>.vi` (`convention: naming.override-names`) |
| `vi name in memory` | `<Lib>.lvlib:<Class>.lvclass:<file name>.vi`; only for a class in no library `<Class>.lvclass:<file name>.vi` |

All seven error outputs 0. The new diagram is class in (and error in) → Call Parent → class out (and error out). The
override is protected and dynamic; a plain-class override keeps its parent's scope. Put it in the class's override
folder (`convention: layout.class-folders`; `kit/pa_class_folder_create_and_move.xml`, or `pa_class_folder_move.xml` when the folder exists; project open and
active; no question needed).
Close the project, read the override cold (state 1), commit. Measured on four AF overrides in skillsaudit M-CLOSE
M3/M4 (2026-10-09) and in the pilot. (pilot rule 6)

## 2. Choose the shape per override

| Override | Hook work | Shape |
|---|---|---|
| Pre Launch Init | `createResources`, the one creating hook: it reads the pre-launch settings (`af-shapes.prelaunch-settings`), creates the resources (`af-shapes.resources`) and cleans up after its own failure (`af-shapes.pli-failure-cleanup`) | F = B-after on class and error (hook measured; the member's case structure unmeasured) |
| Pre Launch Init | start the children (`af-shapes.launch-owner`): send the launch message to self | A (`kit/example_pli_deferred_start.xml`) |
| Actor Core | the helper loop beside Call Parent | A, or C after a series hook |
| Actor Core | a body that returns a changed object to Call Parent | B |
| Actor Core | the stop after Call Parent, then `close` (`af-shapes.stop-site`, `af-shapes.close-vi`) | D, then D-close |
| Stop Core | releases (`af-shapes.resources`, `af-shapes.stop-core-order`); only if it releases something | B-after on the class wire |
| Handle Error | only the local log, or a handler per a plan (`af-shapes.handle-error-order`) | E-after |
| Handle Last Ack Core | only per a relaunch or registration plan (`af-shapes.handle-last-ack`) | H, **unmeasured** |

Pre Launch Init has no `error in`, and its parent does nothing, so the order of work in it is free
(`knowledge/actor-framework.md`). B-after is the measured form in which a hook's error reaches PLI's `error out`, so
a failed create fails the launch. Where there is no error-handling plan, the statement `errors.no-plan-statement`
goes into the class description and Handle Error's VI description (`kit/pa_replace_description.xml`, project
closed). Hook placement here; what each hook VI does is set by the conventions cited.

## 3. Place each hook

Commit before each hook. Project open and active, class loaded. `<C>` = the class's terminal prefix.

**A. Branch beside Call Parent:** `kit/af_add_hook_call.xml`: `vi path` = the override, `class path`, `hook vi path`,
`source terminal name` = `<C> in`, `hook terminal name` = `<C> in`. It taps the **panel** terminal, so the hook runs
beside everything else on that wire. Only the class terminal is wired. (pilot rules 28, 74)

**B. Series before Call Parent:** `kit/pa_insert_series2.xml`: `vi path`, `class path`, `hook vi path`,
`panel name A` = `<C> in`, `hook in A` = `<C> in`, `hook out A` = `<C> out`; the error wire as block B:
`panel name B` = `error in`, `hook in B` = `error in`, `hook out B` = `error out`. Measured on Actor Core (M-CLOSE M4,
all 0). The hook needs both class terminals.

**B-after. Series after Call Parent (roles swapped):** the same helper, with `panel name A` = `<C> out`,
`hook in A` = `<C> out`, `hook out A` = `<C> in`; block B `panel name B` = `error out`, `hook in B` = `error out`,
`hook out B` = `error in`. The hook then sits between Call Parent and the override's outputs. Measured on Pre Launch
Init with both blocks (M-CLOSE M3, all 0, the hook's error 5000 came out of Launch) and on a plain-class override
(pilot). **Stop Core** has no error terminals: block A only, leave `panel name B` empty. Unmeasured on Stop Core (the
measured Stop Core hook sat before Call Parent, the old order). A second B-after hook on the same override lands
between the first and the indicators: unmeasured.
- **Stop Core release errors** (`convention: errors.release-errors`): the release hook's `error out` has nowhere to
  go on Stop Core's pane. Feed it to the project's log VI, or to `Clear Errors.vi` when ignored on purpose, with
  `kit/af_add_hook_call_node.xml`: `source terminal name` = `error out`, `hook terminal name` = `error in`, `hook vi
  path` = that VI. Unmeasured.

**C. Series, then a branch that sees its result:** B first, then `kit/af_add_hook_call_node.xml` with
`source terminal name` = `<C> out` (searched over the diagram's subVI nodes, i.e. the series hook),
`hook terminal name` = `<C> in`. `af_add_hook_call` here would run the branch before the series body. (pilot rule 28)

**D. Stop hook after Call Parent, in a one-frame flat sequence:** `kit/pa_insert_seq_hook.xml`: `vi path` = Actor
Core, `class path`, `hook vi path` = the stop hook, `source terminal name` = `<C> out` of the series hook, or `<C> in`
when Actor Core has none, `hook terminal name` = `<C> in`; defaults `parent terminal name` = `Actor out`,
`order terminal name` = `error out`, `hook order terminal name` = `error in`. Every step 0, `frame count` 1. With
`<C> in` the helper matches the input of another node on that wire, so hook the loop (A) first. Then
`kit/pa_save_member.xml` (`vi path`, `class path`) in a separate call. Result: Call Parent's `error out` enters the
frame as an order tunnel with no consumer; the hook's `error in` is unwired (a fresh chain); its class wire comes
from before Call Parent (`Actor out` is typed `Actor`). (pilot rules 74, 76, 77, 79; M-CLOSE M1)

**D-close. Join the loop and the stop hook into `close`:** after D, commit, then `kit/pa_close_join.xml`:
`vi path` = Actor Core, `class path`, `close vi path` = the `close` member, `loop vi regex` and `stop vi regex` =
patterns matching the loop VI's and the stop hook's VI names, `class terminal name` = `<C> in` (the loop's and
`close`'s class terminal); defaults `merge style` 2147, `indicator label` = `error out`; `remove vi regex` only to
delete an older second hook in the frame. One run makes Merge Errors (loop `error out`, stop hook `error out`) →
`close`, and Merge Errors (Call Parent `error out`, `close` `error out`) → Actor Core `error out`, and rebuilds the
order tunnel. Read `call parent hits`, `loop hits`, `stop hits`, `indicator hits` = 1, `merge class` = `Bundler`,
every error 0. Then `pa_save_member` in a separate call. Measured once on an actor with the project active (~25 s to
generate, < 1 s to run), with `remove vi regex` deleting the old destroy hook; the run with nothing to remove (the
default regex matches nothing) is the same code path but was not run. 5 of 5 stop runs green afterwards (M-CLOSE M1).
> MCP-candidate: add-hook

**E-after. Handle Error, Call Parent first:** a handler that only logs needs class and error: B-after with
`panel name B` = `error out` as above (the parent has already cleared 43, so the log sees real errors only;
`stop actor?` passes from Call Parent untouched). Unmeasured on Handle Error (measured on PLI). A handler that may
overrule `stop actor?` (only per a plan, `convention: errors.plan-required`) needs a third wire, which no kit helper
makes: **unmeasured**, ask before building. The old shape (handler before Call Parent, `panel name B` =
`error in (no error)`) was measured (M-CLOSE M4) and stays only in existing code. > MCP-candidate: add-hook

**F. PLI failure cleanup** (`af-shapes.pli-failure-cleanup`, the user's choice 2026-10-09): the case structure lives
in the member VI `createResources`, never on the override's diagram (the kit cannot wrap existing nodes, and an
override is never regenerated from AIXML). Write `createResources` as AIXML (creates → Merge Errors → a case structure
on the merged error: Error case calls the release VIs, No Error case empty → `error out`; AIXML supports error-cluster
selectors) and generate it as a class member; then hook it into Pre Launch Init as shape B-after (class and error), the
one hook there. Hook placement is measured (B-after, M-CLOSE M3); the generated case structure in `createResources` is
**unmeasured**: sweep it cold and run a forced-failure launch (as M-CLOSE M3) before calling it done.
> MCP-candidate: add-hook

**H. Handle Last Ack Core:** pane read offline from production code: `error in (no error)` 4, `Last Ack` 6, `<C> in` 7, `<C> out`
3, `error out` 0; confirm it with `lvai_connector_pane` first. A hook that takes `Last Ack` needs a wire the kit
helpers do not make; Call Parent's `error out` must reach the override's `error out`. **Unmeasured.**

## 4. Checks

- Close the project. Cold sweep of the class folder, siblings included, and `kit/check_membership.py <class folder>`
  (`ops/sweep.md`), once per override after its hooks.
- Export the override (`lvai_convert_vi_to_aixml`; create the target folder first) and read the shape: B-after shows
  Call Parent's outputs into the hook and the hook's outputs into the indicators; D shows `<Structure _name="Flat
  Sequence Frame">` with a class tunnel into the stop hook and Call Parent's `error out` tunnel with
  `outputs="value:"`; D-close adds two `Merge Errors` nodes, `close` at the top level, and Merge B into `error out`.
- Run (`ops/run-checks.md`) with a timestamped log line per hook, each writer its own file: the order must match
  `knowledge/actor-framework.md`, "Run order, measured".
- Then `ops/cleanup.md` and `ops/icons.md`, only for the overrides and hooks this task made or regenerated.

## 5. Change a hooked method

`lvai_add_class_method` re-run on a method a loaded member calls fails with 56003 after dropping the member entry
(`knowledge/labview-mcp.md`, "lvai_add_class_method"). > MCP-candidate: add-class-method-rerun
- **Replaced by another member with the same pane:** `lvai_swap_subvis` straight onto it (`socket` = the old VI's
  qualified name). It keeps the series wiring and also reaches a node inside the shape-D frame (measured: the stop
  hook swapped in the frame, M-CLOSE M1). Use this route first.
- **Regenerated, the override holds only a branch hook (A):** commit; `kit/pa_delete_subvi.xml` (`vi path`,
  `class path`, `terminal name` = `<C> in`); `kit/pa_clean_member.xml` on that override (the loose end also breaks a
  sibling override; cleaning the edited one fixes both); re-run `lvai_add_class_method`, re-swap its stubs, restore
  scope (`kit/set_scope.py`, project closed) and folder; re-hook with A; cold sweep of every member. (pilot rule 78)
- **Regenerated, the override holds series or several hooks (B to D-close):** `pa_delete_subvi` deletes every
  top-level subVI node with that terminal and leaves the panel terminal unwired, so a series hook cannot be put back.
  Instead: re-run `lvai_add_class_method` on the hook; project closed, `git checkout <bare-override commit> --
  "<override>.vi"` (cold 1); project open, re-hook every shape in its order (B, C, A, D, D-close, each with its
  `pa_save_member`); close, sweep, export, run. (pilot rule 49)
- **The re-run already failed:** close the project, `git checkout` the `.lvclass` and the VI, start again. A name that
  stays held after every caller was unhooked: keep the VI and add the new behaviour as a new hook.

## Report

```
override <class>:<method> created yes/no (errors 0)  protected  dynamic  member  folder <name|asked>
hooks: <hook> shape <A|B|B-after|C|D|D-close|E-after>  helper errors 0  hits <...>  saved by <helper|pa_save_member>
unmeasured shapes used: <none|F|H|E-after 3 wires|B-after on Stop Core>  user asked: <yes/no>
changed: <method> route <swap|unhook-rehook|restore-bare-and-rehook>  pa_clean_member <n/a|run>
sweep <ok>/<n> (siblings incl.), control 0 7, membership ok  export <ok>  run order <as expected>  commits <hashes>
side effects: <files re-saved, project items>   LabVIEW calls <n>   issues: <exact error text or none>
```

## Traps

- `vi name in memory` must be library-qualified for a class in a library. (pilot rule 6)
- `af_add_hook_call` taps the panel terminal: after a series hook it would run first; use `af_add_hook_call_node`.
- `pa_insert_series2` after Call Parent swaps the roles: `hook in` is the `<C> out`/`error out` side.
- A hook's required inputs must all be fed by the helper's one wire per side; one unwired input breaks the override
  and only a cold `lvai_exec_state` shows it. (pilot rule 23)
- `pa_close_join` deletes Call Parent's whole error-out net and rebuilds it. LabVIEW deletes a flat-sequence tunnel
  with no wire on either side, so a helper that wires to the old tunnel fails with 1055; Merge Errors as
  `Function` answers 1057 (`knowledge/labview-mcp.md`, "LabVIEW scripting quirks").
- A shape-D frame built by an older route may keep a class tunnel with no consumer after `pa_close_join` removed its
  second hook (seen in M-CLOSE M1). It is harmless; the export shows it.
- Handle Error runs at every normal stop with 43 on `error in`: a hook chained on the incoming error before Call
  Parent never does its own work. (pilot rule 88)
- Nothing that a hook after Call Parent needs may be released in Stop Core: Stop Core runs inside Call Parent, before
  it (`knowledge/actor-framework.md`, "User events and helper-loop hazards").
