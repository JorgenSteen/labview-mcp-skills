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
  **A plain hook member** (class in, `error in`/`error out`, no calls into other new members) that does not exist
  yet: author it in AIXML with the class as a `path` stand-in, then `lvai_add_class_method` with `methodsJson`
  entries `aixml` + `vi` and `classTerminals` (`["<C> in"]`, or with `<C> out` when it goes in series), no
  `dispatchTerminals` (static); virtual folder `Methods` (`lvai_move_to_folder`); scope private with
  `kit/set_scope.py` (project closed). Members that call other new members: `ops/helper-loop.md` step 2. Measured
  on a teardown hook: added, retyped, state 1 (evaluation 2026-10).
- **Project state:** `lvai_create_override`, `lvai_af_add_hook`, `lvai_af_remove_hook` and every kit helper here need
  the project open and active (the tools open it from `projectPath`); `lvai_exec_state` and the byte-exact scripts
  need it closed (`knowledge/labview-mcp.md`, "Project open or closed, per kind of call").
- **Tools first, kit for the rest.** The override and the shapes A, B, B-after, C and E-after are labview-mcp tools
  (`lvai_create_override`, `lvai_af_add_hook`, `lvai_af_remove_hook`; their shapes, panes and refusals are in
  labview-mcp's `docs/af-override-tools.md`). The kit covers what they refuse or do not offer: a series insert on a
  wire with branches, D, D-close, D-append, a hook fed from a node's error output, Handle Error's third wire
  (`stop actor?`). Kit helpers: generate and run them
  as `knowledge/labview-mcp.md`, "Helper VIs (the kit)" says. Every error output of a helper must read 0. The inputs
  below are the helpers' control labels.
- **Commits:** one before and one after each override and each hook. Keep the commit right after step 1 (the bare
  override): it is the restore point for "Change a hooked method". Save version and loadability on code this session
  did not build: `knowledge/labview-mcp.md`, "Save version" and "A failed, hung or blocked call".

## 1. Create the override

`lvai_create_override(classPath, parentMethod, projectPath)`. `parentMethod` is the AF lifecycle name (`Pre Launch
Init`, `Actor Core`, `Stop Core`, `Handle Error`, `Handle Last Ack Core`), or for a plain class the path of the
parent's `.vi`. `newViPath` only when `convention: naming.override-names` wants another file name than the parent's.
The tool derives the library-qualified name in memory, checks the class's ancestry first and verifies the member
from the saved `.lvclass`; read `failedAtStep` on a refusal.

The new diagram is class in (and error in) → Call Parent → class out (and error out). The override is protected and
dynamic; a plain-class override keeps its parent's scope. Put it in AF Overrides for an actor's AF method, Methods
otherwise (`convention: layout.class-folders`): `lvai_move_to_folder(ownerPath = the .lvclass, folder, itemNames,
projectPath)`, which creates the folder when it is missing; no question needed.
The new override carries NI's help text of the parent method as its VI description: replace it per `convention:
hygiene.descriptions` with the whole new text: `lvai_set_vi_descriptions` (project closed; one entry per VI). (a harness run 2026-10)
Close the project, read the override cold (state 1), commit. Measured on four AF overrides in skillsaudit M-CLOSE
M3/M4 (2026-10-09), in the pilot, and by labview-mcp on five lifecycle overrides in and outside a library
(2026-10-10). (pilot rule 6)

## 2. Choose the shape per override

| Override | Hook work | Shape |
|---|---|---|
| Pre Launch Init | `createResources`, the one creating hook: it reads the pre-launch settings (`af-shapes.prelaunch-settings`), creates the resources (`af-shapes.resources`) and cleans up after its own failure (`af-shapes.pli-failure-cleanup`) | F = B-after on class and error (hook and cleanup shape measured, 2026-10-10) |
| Pre Launch Init | start the children (`af-shapes.launch-owner`): send the launch message to self; the launch itself runs in that message's `Do.vi` | B-after on class and error, so a failed send fails the launch (measured 2026-10-10; body: `kit/example_pli_deferred_start.xml` plus a `<C> out` and its error wired out). Not A: a branch drops the send's error. Beside `createResources`: a second B-after hook is unmeasured, ask |
| Actor Core | the helper loop beside Call Parent | A, or C after a series hook |
| Actor Core | a body that returns a changed object to Call Parent | B |
| Actor Core | the stop after Call Parent, then `close` (`af-shapes.stop-site`, `af-shapes.close-vi`) | D, then D-close |
| Stop Core | releases (`af-shapes.resources`, `af-shapes.stop-core-order`); only if it releases something | B-after on the class wire |
| Handle Error | only the local log, or a handler per a plan (`af-shapes.handle-error-order`) | E-after |
| Handle Last Ack Core | only per a relaunch or registration plan (`af-shapes.handle-last-ack`) | H, **unmeasured** |

Pre Launch Init has no `error in`, and its parent does nothing, so the order of work in it is free
(`knowledge/actor-framework.md`). B-after is the measured form in which a hook's error reaches PLI's `error out`, so
a failed create fails the launch. Where there is no error-handling plan, the statement `errors.no-plan-statement`
goes into the class description (`lvai_set_class_description`, project open and active; CP1252 only) and Handle
Error's VI description (`lvai_set_vi_descriptions`, project closed). Hook placement here; what each hook VI does is set by the conventions cited.

## 3. Place each hook

Commit before each hook. Project open and active, class loaded. `<C>` = the class's terminal prefix.
**Hook terminal names:** the hook's terminal names (the tool's `hookClassIn`/`hookClassOut`/`hookErrorIn`/
`hookErrorOut`, the kit's `hook in`/`hook out`/`hook terminal name`/`in name`/`out name`) must be the hook's names as
its pane has them: read them with `lvai_vi_terminals` first. A member made by `lvai_add_class_method` may name its
error input `error in (no error)` instead of `error in`; pass what the pane says. Panel and Call Parent terminal names
(`panel name`, `far name`) are the override's own and are as written below.

**The tool, for A, B, B-after, C and E-after:** `lvai_af_add_hook(overridePath, classPath, hookViPath, shape,
projectPath)`. Run it with `dryRun: true` first and read the planned wires. It knows each AF override's pane, refuses
before changing anything (a required hook input left unfed, a Handle Error hook before Call Parent, a series insert
into a wire that already branches, the same hook twice, an override with unsaved edits), and saves the override and
the class itself: no `pa_save_member` after it. Its answer gives the execution state read in the project's instance:
read it again cold. Its unsaved-edit check does not see edits made by scripting (labview-mcp measured it), so commit
before each hook as above.

**A. Branch beside Call Parent:** `shape: "branch"`. It taps the **panel** terminal, so the hook runs beside
everything else on that wire. Only the class terminal is wired unless `wireError` is set. (pilot rules 28, 74)

**B. Series before Call Parent:** `shape: "series"`. The hook needs both class terminals; the error chain is wired
where the pane has it. Measured with the kit on Actor Core (M-CLOSE M4) and by labview-mcp with this tool.
- **A wire with branches** (Actor Core whose class wire also feeds the helper loop, the stop frame or `close`): the
  tool refuses it. Use `kit/pa_insert_series_branch.xml`: `vi path`, `hook vi path`, `panel name A` = `<C> in`,
  `hook in A` = `<C> in`, `hook out A` = `<C> out`; block B `panel name B` = `error in`, `hook in B` = `error in`,
  `hook out B` = `error out`; plus `far name A` = Call Parent's class input (`Actor in`, the default), `far name B` =
  `error in`, `far owner class` = `CallParentNode` (a tunnel terminal carries its source's name, so the name alone is
  not enough). It saves the VI only, then `kit/pa_save_member.xml` (`vi path`, `class path`) in a separate call. Read
  `far A found`, `wire A kept branches` (the branches you expect), every error 0. Measured on an Actor Core with three
  branches (loop, stop frame, `close`), all kept, 2026-10.
- **Two series hooks before Call Parent:** each insert lands at the panel side, so the SECOND insert ends up FIRST.
  For hook 1 -> hook 2 -> Call Parent, insert hook 2 first. Afterwards a `<C> in` source search (shape D) matches the
  first hook's input, so the stop's class wire comes from that hook's output (harmless, but surprising). Place series
  hooks before branches (labview-mcp's rule for the tool).

**B-after. Series after Call Parent:** `shape: "seriesAfter"`. The hook then sits between Call Parent and the
override's outputs. Measured on Pre Launch Init with the kit (M-CLOSE M3, the hook's error 5000 came out of Launch) and
on a plain-class override (pilot); labview-mcp measured the tool on Pre Launch Init, Stop Core and Handle Error (both
hooks ran after their Call Parent at the stop). Stop Core has no error terminals; the tool knows the pane. Actor Core
refuses it (`Actor out` is typed `Actor`): use D there. A second B-after hook on the same override lands between the
first and the indicators: unmeasured.
- **Typing, in a DYNAMIC override of a plain class:** the hook's class input AND output are typed as the PARENT
  class; it casts to the child inside as needed. Call Parent's class output carries the run-time-type guarantee, and
  a static subVI keeps it only with the same class in and out. Measured cold (a harness run, 2026-10): child in/child
  out → the override and every caller of the method state 0; parent in/child out (To More Specific Class) → 0;
  parent in/parent out → 1. `lvai_exec_state` says only "VI is not executable".
- **A hook that WRITES a child field** (cast inside, then `Write <field>`) ends with `Preserve Run-Time Class`
  (object in = the written object, target = the hook's input) on its parent-typed output. Returning the written
  object without it: state 0 on the override; passing the input wire straight out: state 1, but the write is lost.
  Read-only and close hooks pass the input wire straight through. (A harness run, 2026-10.)
- **Stop Core release errors** (`convention: errors.release-errors`): the release hook's `error out` has nowhere to
  go on Stop Core's pane. Feed it to the project's log VI, or to `Clear Errors.vi` when ignored on purpose, with
  `kit/af_add_hook_call_node.xml` (`lvai_af_add_hook` taps only a class output): `vi path` = the override,
  `class path`, `source terminal name` = `error out`, `hook terminal name` = `error in`, `hook vi path` = that VI.
  Unmeasured.

**C. Series, then a branch that sees its result:** B first, then `shape: "branchFromNode"` with `sourceHookName` =
the series hook. A plain `branch` here would run the branch before the series body. (pilot rule 28)

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
every error 0, except `delete node error` = 1055 when `remove vi regex` matches nothing (the default). Then
`pa_save_member` in a separate call. Measured once on an actor with the project active (~25 s to generate, < 1 s to
run), with `remove vi regex` deleting the old destroy hook. 5 of 5 stop runs green afterwards (M-CLOSE M1). Since
2026-10-12 that Delete is outside the error chain (before, a no-match 1055 skipped every later step and left the VI
half rewired and unsaved), and the stop hook's and `close`'s error input is found as `error in` or
`error in (no error)` (hooks made by `lvai_add_class_method`). That version is measured: all hits 1, `merge class`
`Bundler`, `delete node error` 1055 with the default regex, runs green afterwards (evaluation 2026-10).
> MCP-candidate: add-hook

**D-append. A further hook in the stop frame of Actor Core:** after Call Parent returns, the actor's message loop has
ended, but a helper loop has NOT: the D frame runs right after the stop is sent, before the loop exits (the appended hook ran 2-100 ms before the loop's last line, 7 of 7, measured in an evaluation, 2026-10). So D-append is for work that must
follow the stop but not the loop. **Work that must follow the loop's exit belongs in `close`** (D-close runs it after
both the loop and the stop): extend the `close` member instead. Actor Core has no `<C> out` after Call Parent (`Actor
out` is typed `Actor`), so B-after does not apply. The hook goes into D's frame after the stop hook:
`kit/pa_append_seq_hook.xml`: `vi path` = Actor Core, `class path`, `hook vi path`, `source terminal name` = the class
wire from BEFORE Call Parent as D uses it (`<C> out` of the series hook, or `<C> in`), `hook terminal name` = the
hook's class input, `prev order terminal name` = the stop hook's error output, `hook order terminal name` = the hook's
error input (read with `lvai_vi_terminals`). Then `pa_save_member`. It works before or after D-close (run after it,
measured in an evaluation, 2026-10). The appended hook's `error out` is left unwired: end it in `Clear Errors` INSIDE the frame
(`convention: errors.ignored-errors`); neither `lvai_af_add_hook` nor `af_add_hook_call_node.xml` can do that (they reach top-level nodes only),
so use `kit/pa_frame_hook_sink.xml` (`node vi regex` = the hook, `sink vi path` = `Clear Errors.vi`'s path in
vi.lib, dry run first, then `apply` T). `Clear Errors`' input is named `error in (no error)`; `lvai_vi_terminals` cannot
read it (it lives in an `.llb`). Measured on Actor Core: frame found, hook wired, state 1 (measured in an evaluation, 2026-10).

**E-after. Handle Error, Call Parent first:** a handler that only logs needs class and error: `shape:
"seriesAfter"` (the parent has already cleared 43, so the log sees real errors only, 1608 of an Emergency Stop
included; `stop actor?` passes from Call Parent untouched). labview-mcp measured it on Handle Error (the hook ran after
Call Parent at the stop).
- **A handler that may overrule `stop actor?`** (only per a plan, `convention: errors.plan-required`) is a second body
  after the first, on the third wire: `stop actor?` and `error out`. `lvai_af_add_hook` cannot wire `stop actor?`; use
  `kit/pa_insert_series2.xml` after the log hook, roles swapped as after Call Parent: `vi path`, `class path`, `hook vi
  path`, `panel name A` = `stop actor?`, `hook in A` = `stop out`, `hook out A` = `stop in`; block B `panel name B` =
  `error out`, `hook in B` = `error out`, `hook out B` = `error in` (names as the body's pane has them); then
  `pa_save_member`. The body needs no class terminal (`error in`, `stop in` → `error out`, `stop out`). Measured
  2026-10-10 (an AF measurement series): the override read Call Parent → class/error body → `stop actor?`/error body
  → indicators, and the body kept the actor running on 5003 while the control stopped
  (`knowledge/actor-framework.md`, "Which order can keep an actor running"). **The parent answers T at a Normal Stop
  too:** the body overrules only the codes the plan names, or the actor ignores its own Normal Stop.
- The old shape (handler before Call Parent) was measured (M-CLOSE M4) and stays only in existing code; the tool
  refuses it unless `allowHandleErrorBeforeCallParent`. > MCP-candidate: add-hook

**F. PLI failure cleanup** (`af-shapes.pli-failure-cleanup`, the user's choice 2026-10-09): the case structure lives
in the member VI `createResources`, never on the override's diagram (the kit cannot wrap existing nodes, and an
override is never regenerated from AIXML). Write `createResources` as AIXML (creates → Merge Errors → a case structure
on the merged error: Error case calls the release VIs, No Error case empty → `error out`; AIXML supports error-cluster
selectors) and generate it as a class member; then hook it into Pre Launch Init as shape B-after (`seriesAfter`, class
and error), the one hook there. Measured: hook placement (B-after, M-CLOSE M3), and the cleanup shape on 2026-10-10
(an AF measurement series: a forced error after a create made Launch return it, the Error frame's release answered 0
and a chained status read proved the refnum gone, no Stop Core, 2 of 2; `knowledge/actor-framework.md`, "PLI's own
cleanup works"). Still sweep each new `createResources` cold and run one forced-failure launch, because its creates
and releases are the project's own. Order a check after a release by its error wire.
- **The refnum check** (`af-shapes.pli-failure-cleanup`): after the creates, `Read` the events (fresh error chain) →
  Unbundle By Name → `Not A Number/Path/Refnum?` per refnum → Select(error cluster with the project's code, no error)
  → into the same Merge Errors as the creates.
- **Generate `createResources` on `grpc`** (`backend: "grpc"` on `lvai_add_class_method`). The `pylabview` composer
  writes an error-cluster case structure (`Error`/`No Error`) that loads broken ("Selector values are not unique / No
  case for some selector values") while the tool answers ok and verifiedOnDisk; only the cold sweep shows it
  (`knowledge/labview-mcp.md`, "The AIXML backend"). Measured 2026-10-26.
- **The forced-failure launch:** with the project open, `lvai_swap_subvis` the create call inside `createResources`
  (e.g. `createEvents`) onto a same-pane member that creates nothing (`init` served) or one that returns an error;
  save; close the project; run ONE launch through the launcher (`ops/run-checks.md`). Expect: Launch returns the
  guard's (or the forced) error, no Actor Core log line, no Stop Core, no Handle Error, the launcher back within its
  timeout. Then, project closed, `git checkout -- "<createResources>.vi"` and sweep cold; never commit the swap. A
  Launch 0 with a hang at stop means the refnum check is missing (`knowledge/actor-framework.md`, "A create that
  creates nothing"): kill only with the user's go-ahead. Measured 2026-10-26, 3 of 3 with the check.

**H. Handle Last Ack Core:** pane read offline from production code and with `lvai_connector_pane` from NI's VI
(2026-10-10, pattern 4812): `error in (no error)` 4, `Last Ack` 6, `<C> in` 7, `<C> out` 3, `error out` 0; confirm it
on your LabVIEW. A hook that takes `Last Ack` needs a wire the kit
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

`lvai_add_class_method` re-run on a method a loaded member calls fails with 56003 after dropping the member entry, and
in 2.2 it failed the same way with no loaded caller at all (`knowledge/labview-mcp.md`, "lvai_add_class_method").
> MCP-candidate: add-class-method-rerun
- **A new body for a series hook** (e.g. `createResources` hooked B-after into PLI), measured 2026-10-26: commit;
  `lvai_af_remove_hook` (`dryRun` first; read `bypassed`, `sinksReconnected`); close the project;
  `kit/remove_members.py <.lvclass> "<hook>.vi"` (no `--delete-files`); open; `lvai_add_class_method` as a FIRST run
  with the new AIXML (a re-run gave 56003, see above; `grpc` for an error-cluster case structure, shape F); re-swap its
  stubs; `lvai_af_add_hook` with the shape it had (`seriesAfter`, dry run first); then scope and folder again, because
  a first run puts the member public at the class root (`lvai_move_to_folder`; `kit/set_scope.py`, project closed);
  close, cold sweep, `check_membership.py`, export, run.
- **Replaced by another member with the same pane:** `lvai_swap_subvis` straight onto it (`socket` = the old VI's
  qualified name). It keeps the series wiring and also reaches a node inside the shape-D frame (measured: the stop
  hook swapped in the frame, M-CLOSE M1). Use this route first.
- **A hook taken out, no regeneration** (`knowledge/labview-mcp.md`, "Small fixes: edit in place"):
  `lvai_af_remove_hook(overridePath, classPath, hookName, projectPath)`, `dryRun: true` first. It deletes one node
  (`occurrence` when the name is on the diagram twice), bypasses a series hook (each output read is bridged to the
  input of the same stem), runs Remove Bad Wires, saves the override, only the siblings it left modified, and the
  class, and does not save an override it left broken (`removeBrokeOverride`). Read `bypassed` and
  `sinksReconnected`. Prefer it to the restore-bare-and-rehook route below.
- **The tool refuses a series hook** (`seriesHookNotRemovable`: an output with no input of its stem): the kit's
  `kit/pa_remove_series_block.xml` once per wire pair: `vi path`, `node vi regex` = the hook, `in name`/`out name` =
  `<C> in`/`<C> out`, then `error in`/`error out` with `delete node` T on that last pair. It does every lookup first,
  deletes the two wires (and the node), and bridges the source to every other branch and every far end. Read `node
  hits` 1, `kept count` and `sink count` = the branches you expect, `new wire broken` F, every error 0; then
  `pa_save_member`. Measured 2026-10 on an Actor Core (a kept frame tunnel, Call Parent as the far end).
- **Putting a hook back:** before Call Parent, shape B (`pa_insert_series_branch` on a wire with branches); after
  Call Parent in Actor Core, shape D-append or, after the loop's exit, inside `close`.
- **A hook with a third output wire** (e.g. `init`'s registration refnum into the loop): `pa_remove_series_block`
  handles the class and error pairs only. The third wire is left one-ended (cold state 0): run `pa_clean_member` after
  the removal, and after the put-back re-wire it with `kit/pa_wire_nodes.xml` (measured in an evaluation, 2026-10).
  Whether `lvai_af_remove_hook` bridges or refuses a third output is unmeasured: dry run first.
- **Regenerated, the override holds only a branch hook (A):** commit; `lvai_af_remove_hook` on that hook (it cleans
  the loose end in the override and the sibling it breaks, pilot rule 78); re-run `lvai_add_class_method`, re-swap
  its stubs, restore scope (`kit/set_scope.py`, project closed) and folder; re-hook with A; cold sweep of every
  member.
- **Regenerated, the override holds series or several hooks (B to D-close):** re-run `lvai_add_class_method` on the
  hook; project closed, `git checkout <bare-override commit> -- "<override>.vi"` (cold 1); project open, re-hook every
  shape in its order (B, C, A, D, D-close, each saved as its section says); close, sweep, export, run. (pilot rule 49)
  Removing the hooks one by one with `lvai_af_remove_hook` instead of the checkout is unmeasured on a D/D-close
  override.
- **The re-run already failed:** close the project, `git checkout` the `.lvclass` and the VI, start again. A name that
  stays held after every caller was unhooked: keep the VI and add the new behaviour as a new hook.

## Report

```
override <class>:<method> created yes/no (errors 0)  protected  dynamic  member  folder <name> (created|moved)
hooks: <hook> shape <A|B|B-after|C|D|D-close|E-after> by <lvai_af_add_hook|kit helper>  errors 0  hits <...>  saved by <tool|helper|pa_save_member>
unmeasured shapes used: <none|H|second B-after on PLI>  user asked: <yes/no>
changed: <method> route <swap|lvai_af_remove_hook|pa_remove_series_block|restore-bare-and-rehook>  pa_clean_member <n/a|run>
sweep <ok>/<n> (siblings incl.), control 0 7, membership ok  export <ok>  run order <as expected>  commits <hashes>
side effects: <files re-saved, project items>   LabVIEW calls <n>   issues: <exact error text or none>
```

## Traps

- The name in memory of a new override must be library-qualified for a class in a library; `lvai_create_override`
  derives it, a hand-run helper does not. (pilot rule 6)
- `branch` taps the panel terminal: after a series hook it would run first; use `branchFromNode`.
- A child-typed hook after Call Parent in a dynamic plain-class override reads state 0 with only "VI is not
  executable", and breaks every caller of the method too: type the hook's class terminals as the parent (B-after,
  "Typing"); a hook that writes a field ends with `Preserve Run-Time Class`.
- A hook's required inputs must all be fed by one wire per side; one unwired input breaks the override and only a
  cold `lvai_exec_state` shows it. `lvai_af_add_hook` refuses such a hook; the kit helpers do not. (pilot rule 23)
- `pa_close_join` deletes Call Parent's whole error-out net and rebuilds it. LabVIEW deletes a flat-sequence tunnel
  with no wire on either side, so a helper that wires to the old tunnel fails with 1055; Merge Errors as
  `Function` answers 1057 (`knowledge/labview-mcp.md`, "LabVIEW scripting quirks").
- A shape-D frame built by an older route may keep a class tunnel with no consumer after `pa_close_join` removed its
  second hook (seen in M-CLOSE M1). It is harmless; the export shows it.
- Never `lvai_graft_diagram` into an override, not even in place with a copy: with the project open it raised a
  modal dialog and then crashed LabVIEW, and a finished graft would delete Call Parent
  (`knowledge/actor-framework.md`, "Never graft a diagram into an override"). Bodies go in by hooks.
- Handle Error runs at every normal stop with 43 on `error in`: a hook chained on the incoming error before Call
  Parent never does its own work. (pilot rule 88)
- Nothing that a hook after Call Parent needs may be released in Stop Core: Stop Core runs inside Call Parent, before
  it (`knowledge/actor-framework.md`, "User events and helper-loop hazards").
