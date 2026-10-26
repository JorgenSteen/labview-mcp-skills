# Helper loop: build an actor's loop VI and wire it into Actor Core

**When:** a task adds a helper loop to an actor (a UI or panel loop, an acquisition or producer loop, a loop on user
events), adds user events for one, or changes how a loop is registered or stopped.

**What it gives:** the events typedef and its field, the role members (`createResources`, `createEvents`, `init`,
`stop`, `close`, senders), the loop VI as a private class member with the registration refnum from `init` wired
through the event structure's dynamic terminal, the hooks on Pre Launch Init and Actor Core, every member executable
cold, and runs in which the actor stops cleanly (also right after launch and after a loop error).

**Not here:** creating the overrides and each helper's inputs for a hook (`ops/override.md`, sections 1 and 3: shapes
F, A or C, B on a wire with branches, D, D-close); the events field route (`ops/class-field.md`, route A); a new actor class (the class-generator agent, below);
how AF and user events behave (`knowledge/actor-framework.md`, "User events and helper-loop hazards"). In local mode,
or when a concern is off, follow the surrounding code instead.

## Before you start

- **Setup level:** a new loop is level 4 (af-shapes, naming, layout, errors). Conventions used:
  `af-shapes.one-pattern-per-area`, `af-shapes.helper-loop-vi`, `af-shapes.helper-loop-error-case`,
  `af-shapes.registration`, `af-shapes.stop-mechanism`, `af-shapes.stop-site`, `af-shapes.close-vi`,
  `af-shapes.timed-work`, `af-shapes.events-typedef`, `af-shapes.global-events`, `af-shapes.resources`,
  `naming.role-names`, `naming.method-case`, `layout.class-folders`, `layout.scope`, `layout.accessors-on-demand`,
  `errors.loop-errors`, `errors.ignored-errors`, `errors.log-local`.
- **Ask before the build** (the main session, before any brief): the actor's name with its `<ABBR>` and `<name>` parts
  per `naming.class-library-names` (a subagent never invents or changes a name); for the first actor of a project,
  the log mechanism (`errors.log-local`: where the loop and `close` log an error); whether the actor has pre-launch
  settings (`af-shapes.prelaunch-settings`; none = no `prelaunchSettings` field and no `writePrelaunchSettings`).
- **Maintenance scope.** An existing actor keeps its loop, stop and teardown shape (for example a Stop Core that
  generates and destroys) unless the task is to change it. A second loop in that actor follows its first loop.
- **The actor class exists, in its own library** (`convention: layout.library-per-actor`). A new class comes from
  labview-mcp's class-generator agent, briefed per `session/brief.md` with the parent
  `vi.lib\ActorFramework\Actor\Actor.lvclass`, NO fields (step 1 makes `events`; `prelaunchSettings` only when the
  actor has settings), no accessors, and the folder, naming and scope rules from that file's table; check it
  afterwards as that file says. Then the library around it: `knowledge/labview-mcp.md`, "A new project or a plain
  library" (do it before the members, so the class is not re-saved later; measured in an evaluation, 2026-10).
- **The kind of loop** (`convention: af-shapes.stop-mechanism`): every loop VI has at least one loop on an async stop
  (a user event by default). Variant 1 is that event loop alone; variant 2 adds other loops (timed producer, polling)
  in the same VI, stopped by the local `stop` the event loop sets; each of them calls the actor's `stop` member when
  it ends, so the event loop ends too. A polling-only loop VI therefore gets an event loop
  too. A notifier instead of the user event is allowed by the convention and measured as a stop signal (about one
  loop period, `knowledge/actor-framework.md`), not built by this route; a queue is not measured here.
- **Build order, project state, commits:** `knowledge/labview-mcp.md`, "Evidence, git, build order" and "Project open
  or closed, per kind of call". Commit before each structural step (typedef, field, each member, the loop, each hook).

## Steps

1. **Events typedef and field** (`convention: af-shapes.events-typedef`): `ops/class-field.md`, route A. Type
   spelling e.g. `cluster{ref{UserEvent}{bool.stop}.stop,ref{UserEvent}{string.error}.error}`; the suffix labels the
   element, which the event frames select (`knowledge/labview-mcp.md`, "lvai_create_typedef ..."). Make `Read
   events` and `Write events` only when step 2 uses them. Global events: `convention: af-shapes.global-events`.
   > MCP-candidate: user-event-cluster
2. **Role members:** `createResources`, `createEvents`, `init`, `stop`, `close` and any sender, named per
   `convention: naming.role-names`; their content per `af-shapes.resources`, `af-shapes.pli-failure-cleanup`,
   `af-shapes.events-typedef`, `af-shapes.registration`, `af-shapes.stop-site`, `af-shapes.close-vi`.
   - `createResources`: the one Pre Launch Init hook; calls `createEvents` (and creates any other resource), cleans
     up on its own error (`ops/override.md`, shape F, for its AIXML).
   - `createEvents`: creates the user events and writes the `events` field.
   - `init`: `Read events` on a fresh error chain → `Unbundle By Name` → `Register For Events` on a fresh "no error"
     constant, its refnum output left unwired (step 11 puts it on the pane); `error out` = Merge Errors (`error in`,
     `Read events`' error, Register's error); for a root that launches nested actors, the launches too (as subVIs).
   - `stop`: `Read events` → Generate the stop event. `close`: per `af-shapes.close-vi`; work that must follow the
     loop's exit (a final log line) goes here, not into the D frame.
   - Their virtual folder: `Methods` (`convention: layout.class-folders`). A member with NO class terminal (a pure
     function such as a `tick`) joins the class with `lvai_add_to_class(lvclassPath, itemPaths, projectPath, folder =
     "Methods")`. The VI Server route is measured (the kit, an evaluation 2026-10); labview-mcp lists the tool's
     adding of a `.vi` as unmeasured: check the `.lvclass` afterwards.
   Author each in AIXML with the class as a `path` stand-in and the accessors as `lvai_placeholder_subvi` stubs.
   **Class terminals per member:** a member that goes in series on the class wire or writes a field returns the
   object: `createResources`, `createEvents` and `init` declare `<C> in` AND `<C> out` in their AIXML and get
   `classTerminals` = `["<C> in", "<C> out"]`; `stop` and `close` take `<C> in` only (`["<C> in"]`).
   Then `lvai_add_class_method` (`methodsJson` entries with `aixml`, `vi` and their `classTerminals`, no
   `dispatchTerminals` = static; `projectPath`) in batches by call order: members that call no other new member
   first (`createEvents`, `close`, `stop`, `init`), then the ones that call them (`createResources`), so a stub never
   stands in for a member that exists already (one call for all failed, measured in an evaluation, 2026-10). A refnum-cluster constant in
   AIXML needs `value="[]"`. Then one `lvai_swap_subvis`
   with `editsJson` for every stub (`kit/make_batch_json.py` builds it; it warns on a shared stub). Measured: two
   members, two stubs each, one call each (M-CLOSE M1). Scope private with `kit/set_scope.py` (project closed). Commit.
   **The loop VI does not destroy the events:** it does Unregister only, and `close` destroys. The measured proof's
   loop VI still destroyed them itself and `close` destroyed them again (error 0, 5 of 5): do not copy that, and do not
   build on a second destroy answering 0.
3. **Loop VI AIXML** at the member path (`convention: af-shapes.helper-loop-vi`), class terminal `<C> in` as a `path`
   stand-in, accessor and `Send` calls as stubs:
   - **Registration, outside the loop, for now** (`convention: af-shapes.registration`): author it in the loop VI as
     below, because the dynamic wiring (step 5) needs a Register node to wire from; step 7b then replaces it with a
     refnum input fed by `init`. `Read events` → `Unbundle By Name` →
     `Register For Events` with one `event source` per element (the measured form; the whole cluster compiles, not run
     here) and **no incoming error** (a fresh "no error", measured in the pilot) → the loop(s) → `Unregister For
     Events` → `Merge Errors` (`error in`, the loop's error, Unregister's) → `error out`. Leave Register's output and
     Unregister's `event registration refnum` input unwired, and author **no** refnum `<Tunnel>`: the dynamic wiring is
     step 5.
   - **The error case, inside the loop** (`convention: af-shapes.helper-loop-error-case`): `error in` enters the loop in
     a shift register; a `<Structure _name="Case Structure">` with `selectin` = that error. Error frame: the loop's stop
     terminal T, the error passed on. No Error frame: the event structure (or the loop's work). The AIXML reference
     lists error-cluster selectors (`No Error`, `Error 1..5`, `Default`). Every output tunnel needs a value in both
     frames (the refnum tunnel step 5 creates is the exception: step 5 sets its flag). Built and run in a harness run
     (2026-10, state 1 after steps 5–7).
   - Frames select the element label, e.g. ` <stop>\3A User Event `. Timeout frame per `convention:
     af-shapes.timed-work`; an event structure whose frames are all user events needs an empty one for the spec step (step 5).
   - Sends to its own actor: `Read Self Enqueuer` → a generated `Send <method>.vi` (protected: the VI must be a member).
     The message class must exist first (`lvai_create_message_class`; messages before overrides, `knowledge/labview-
     mcp.md`, "Evidence, git, build order"); in this AIXML the `Send` VI is a stub, swapped in step 9.
     Loop errors per `convention: errors.loop-errors` (measured: the project's error method, then `Send Normal Stop`
     to self).
   - Variant 2: one VI, the locals by `<Node _name="Local Variable" element="stop" .../>` (`inputs=` writes,
     `outputs=` reads); `stop` written F before the loops (`af-shapes.stop-mechanism`); the producer's read of `stop`
     sequenced after its `Wait (ms)` (unsequenced it costs up to two intervals: `knowledge/actor-framework.md`);
     after each non-event loop, a Flat Sequence with the actor's `stop` member → `Clear Errors` on its error, so a
     loop that ends on an error stops the event loop too. `stop` is a stub here like the accessors, swapped in step 9.
   - `kit/example_helper_loop.xml` is an older body with a notifier exit: copy spellings from it, not its stop shape.
4. **Generate**, project closed: `lvai_generate_vi_with_events(aiXmlFilePath, viPath = <member path>)`. `ok:false` and
   state 0 are expected until step 9 (the stubs and the unwired registration); any other refusal (a parse error, a
   missing frame in the export) is a real failure. It refuses two event structures in one document. It keeps an event
   structure nested in a case frame inside the loop (measured 2026-10). > MCP-candidate: generate-with-events-fixes
   A panel control with a static event (e.g. a `Stop` button) gets its Value Change frame from the generator itself;
   that row survives step 7 (`--check` lists it as a static row) (a harness run, 2026-10).
5. **Both sides of the registration, the specs and the tunnel flag**, project open and active (the VI is not a member
   yet; opening the project with it in memory can adopt it as a loose top-level item: after step 9, check the
   `.lvproj` with the project closed and drop a leftover loose entry with `lvproj_drop.py`):
   `lvai_wire_dynamic_events(viPath)` with its defaults (`wireRightSide`, `finishUserEvents` true). It finds the event
   structure at any depth (the error-case shape: loop → case frame → event structure), wires Register's refnum output to
   the dynamic terminal (`sourceFrom` = the diagram, since step 3 authors no refnum tunnel) and the right-side terminal
   to Unregister, writes the user-event specs of every user-event frame from the `dynIndex` the generator wrote, and
   sets "Use Default if Unwired" on the case tunnel this wiring created (only that one). Its bundle step CLOSES AND
   SAVES the active project (`projectClosed`, `projectClosedFor`). Read `eventStructuresFound` 1, `rightSide` (not
   skipped), `userEventStep`, `useDefaultSet` = the one new tunnel; then render the diagram (`lvai_render_diagrams`):
   the tool says a render is the only proof of the wire. A VI generated before 2026-10-10 is refused (it carries
   `dynIndex` 1 on every frame): regenerate it. These are labview-mcp's fixes for the measured gaps of this step; the
   tool on this exact shape is not yet measured here: if it refuses, stop and report (the kit route it replaced is in
   `kit/README.md`, "Retired").
   > MCP-candidate: wire-dynamic-events-fix
6. *(merged into step 5.)*
7. **Check the specs and the flag offline**, project closed: `pylv_extract`, then
   `python <skill>/kit/set_user_event_specs.py <bundle> <base> --check` and
   `python <skill>/kit/set_use_default.py <bundle> <base> --check`. `<bundle>` = the folder `pylv_extract` wrote,
   `<base>` = the VI's file name without `.vi` (the bundle's files are `<base>_*.xml`). Expect one spec row per
   user-event frame with its `dynIndex` (`diagramIdx` = the frame's 0-based position in the event structure's frame
   list as the AIXML export lists it, Timeout included; `dynIndex` = the source's 1-based position on Register), plus
   any static row the generator made; measured rows: `0:error:2 2:stop:1`, `1:stop_event:1`. `set_use_default.py
   --check` flags EVERY case output tunnel left unwired in a frame, which in hand-built code can hide a real missing
   wire: anything besides the new refnum tunnel, stop and wire or report it. Should step 5 have left a row or the flag
   unset, the same scripts without `--check` write them (`set_user_event_specs.py <bundle> <base>
   <diagramIdx>:<element label>:<dynIndex> ...`), then `pylv_rebuild`. Cold state 1 with the flag, 0 without
   (measured 2026-10). (pilot rules 39, 60)
7b. **Registration refnum as an input** (`convention: af-shapes.registration`), project open and active, edited in
   place: `kit/pa_reg_to_control.xml` (`VI Path`, `term index` = a free INPUT slot of the pane: read the pane with
   `lvai_connector_pane` and take a slot with no terminal on the input side; measured 10 with the class and error
   terminals at 11, 8, 3, 0). It creates
   a control on Register's refnum input (typed like the registration), deletes Register, its Unbundle and the fresh
   constant (another consumer of the Unbundle is reconnected), wires the control to the loop tunnel Register fed, and
   puts it on the pane. Read `register count` 1, `new wire ends` 2, `new wire broken` F, `on pane` T, every error 0.
   `Read events` stays when its error feeds the loop; Unregister's `error in` is then unwired (no error). Re-check
   step 7 offline afterwards: the spec rows and the use-default flag are unchanged (measured). It runs no Remove Bad
   Wires on purpose (that would remove the inner refnum chain before the new wire exists). It leaves `Read events` with
   a dangling output when Unbundle was its only consumer: after step 9, run `kit/pa_clean_member.xml` on the loop VI
   (cold state 0 → 1, measured in an evaluation, 2026-10); the dead `Read events` node stays until removed by hand or by a later edit.
7c. **Refnum through the Error frame** (`convention: af-shapes.registration`), project CLOSED, after 7b and its
   `pa_clean_member` (so after step 9): `kit/pa_reg_through_error_frame.xml` (`vi path`, `variant` 1, `refnum label`
   = the control's label from 7b), `apply` F first. Read `control hits` 1, `unregister hits` 1, `case out inner count`
   and `case in inner count` 2, `error frame index` = the Error frame, `variant 1 ready` T, every lookup error 0; then
   `apply` T: `v1 wire ends` 2, `v1 wire broken` F, `v1 save error` 0. `vi_nets.py` before and after: exactly one
   new wire, inside the Error frame, between the two case tunnels. Cold state 1. The use-default flag from step 7
   stays set and is now unused (no route clears it; harmless). Never run `variant` 2: it is the measured failure
   (Unregister fed from the control hangs every stop). Without this step an Error-frame exit hands Unregister a null
   refnum (1055, hidden by the Merge order). Measured in an evaluation, 2026-10: normal stop 5/5, early stop 5/5,
   forced Error-frame exit clean.
8. **Event data**, project closed, only for a frame that reads its payload: `lvai_set_event_data_fields(viPath,
   fields="<dataNodeUid> <placeholderUid>:4")`. Both uids are the ones the step-3 AIXML wrote: the frame's Event Data
   Node, and a labelled constant `Payload Placeholder` wired into the primitive or subVI input that consumes the field
   (author it in step 3; an indicator or tunnel cannot be the sink). `4` = the first payload item (0 Source, 1 Type,
   2 Time, 3 the event refnum; 4 and 5 for a two-element cluster); at most two fields per frame. `ok:false` before
   membership is expected: read the frame's data node again after step 9 (export or cold state).
9. **Membership:** `lvai_add_class_method` with the **existing VI only** (`methodsJson`
   `[{"vi": "<member path>", "classTerminals": ["<C> in"]}]`, `projectPath`); after it, check the `.lvproj` for a
   loose entry of the loop VI (step 5). With `aixml` as well it re-converts the
   VI and steps 5–8 (7b included) are lost. Then `lvai_swap_subvis` the stubs; scope private (`kit/set_scope.py`, project closed);
   the folder `Helpers` (`convention: layout.class-folders`): `lvai_move_to_folder` (creates the folder when missing;
   project open and active; no question needed). (pilot rule 91)
   > MCP-candidate: add-class-method-rerun, move-to-folder
10. **Panel and controls** (`knowledge/labview-mcp.md`, "LabVIEW scripting quirks", panel flags and mechanical action):
    - a loop with a user-facing panel only: `kit/pa_set_panel_on_call.xml` (project open and active), read back cold
      with `kit/pa_read_panel_on_call.xml`; re-apply after any regeneration;
    - a Stop button a test must press: Switch When Released, reset to F by a local in its own frame (author the local
      in AIXML), then `kit/pa_set_mechanical_action.xml` (`mechanical action` 1, project closed);
    - variant 2's `stop`: off the pane, hidden with `kit/pa_set_control_visible.xml` (project closed). It must be a
      SWITCH, never a latch (a latched Boolean cannot have a local variable): a new Boolean control is Switch When
      Pressed (0) by default, so nothing to set. Prove it cold with `kit/pa_read_boolean.xml`: mechanical action 0 or
      1 (not 3–5), visible F (the export shows neither).
    > MCP-candidate: control-property-setters
11. **Wire it into the overrides**, each hook by `ops/override.md` (section 1 to create an override; section 3: F,
    A or C, B on a wire with branches, D, D-close), commit and `pa_save_member` as that file says:
    - Pre Launch Init: `createResources` is the one Pre Launch Init hook (shape F), so a failed create fails the
      launch and is cleaned up (`af-shapes.pli-failure-cleanup`).
    - `init` first, project open and active: `kit/pa_reg_indicator.xml` (`VI Path` = `init`, `term index` = a free
      OUTPUT slot read with `lvai_connector_pane`, measured 2) creates the refnum indicator on Register's output and puts it on the pane (`on pane` T,
      errors 0); then `pa_save_member`, and scope private (`kit/set_scope.py`, project closed).
    - Actor Core, in this order: the loop as shape A from `<C> in` (or C after a series hook); the `stop` hook as
      shape D (`source terminal name` = `<C> in` finds the loop's node on that wire); then shape D-close with
      `close vi path` = `close`, `loop vi regex` = the loop VI's name, `stop vi regex` = the stop hook's name. The
      current D-close version is measured (evaluation 2026-10): read its answers as `ops/override.md` lists them.
    - Then `init` in series before Call Parent (class and error): `kit/pa_insert_series_branch.xml` (shape B on a wire
      with branches, `ops/override.md`): `wire A kept branches` = the loop, the stop frame and `close`. Then
      `kit/pa_wire_nodes.xml`: `source vi regex` = `init`'s name, `source terminal name` = `event registration
      refnum`, `sink vi regex` = the loop VI's name, `sink terminal name` = the label of the control step 7b made
      (`event registration refnum`); `source hits` and `sink hits` 1, `wire ends` 2, `wire broken` F. It does not save:
      `pa_save_member`. Measured on two actors, 2026-10 (one of them a root whose `init` also launches the nested
      actors).
    - The kit's branch hook wires the class terminal only: the loop's `error in` stays unwired (no error), as in the
      measured run. That is the user's decision (2026-10-09): no extra wiring.
    - No Stop Core override is made for the loop (`convention: af-shapes.resources`).

## Checks

- Close the project. Cold sweep of the class folder with a negative control, and `kit/check_membership.py <class
  folder>` (`ops/sweep.md`). State 0 on the loop before step 9 is expected; after it, every member reads 1.
- Export the loop VI (`lvai_convert_vi_to_aixml`; create the folder first): no Register node; the `event registration
  refnum` control on the pane feeding a loop `<Tunnel>` whose inside net has no consumer in the export (the dynamic
  terminal has no AIXML element), the case structure with both frames inside the loop, Unregister after it fed by a
  loop output tunnel (never by the control), the refnum wired through the Error frame (step 7c; `vi_nets.py` shows
  the wire), no refnum `<Tunnel>` on the event structure; variant 2 lists its locals (init write, event-loop
  write, producer read). `python <skill>/kit/vi_nets.py <vi>` shows the dynamic terminal's wire offline.
- Export Actor Core: `init` (`<C> in`, `error in`) → Call Parent (`Actor in` = `init`'s `<C> out`, `error in` =
  `init`'s error); the loop takes `<C> in` from the panel and the refnum from `init`; then the D-close shape
  (`ops/override.md`, "Checks").
- **Early stop ×5:** launch the actor and send Normal Stop right after launch: the headless launcher VI of
  `ops/run-checks.md` ("Behaviour runs", headless run) with its run time 0, five times: every stop code 0, the caller
  gets the Last Ack each time, no hang, the loop and Actor Core read 1 cold afterwards. For a root, also make a nested
  launch fail on purpose (e.g. pre-launch settings the child's `createResources` must refuse, such as an invalid
  folder): the root must stop by itself and its Last Ack must carry the nested error. Measured 2026-10 on two actors, 5 of 5 each (`knowledge/actor-framework.md`).
- Run (`ops/run-checks.md`) with timestamped lines, each writer its own file (`knowledge/actor-framework.md`,
  "Observing and testing actors"): the stop line, the loop's exit, then `close` after both. Measured: `close` 20–112 ms
  after the later of the two, error 0, 5 of 5, one of them with a launcher that exits at once and a stop ~16 s later
  (M-CLOSE M1). Actor Core and the loop read 1 cold after the run. Per-writer lines that the members do not write
  themselves: instrument only throwaway copies or the launcher (e.g. the launcher's stop-to-ack time), never leave
  probes in members (evaluation 2026-10).
- Variant 2: test the `stop` reset by N launches of the actor from one caller (the loop VI is private and needs
  `init`'s refnum, so it cannot be called directly; two tool runs unload it in between). Measured: 5 launches in one
  launcher call, 10 ticks each (evaluation 2026-10).
- Variant 2: make the producer fail on purpose: `lvai_swap_subvis` its work subVI onto a throwaway VI with the same
  pane that returns a custom error, run, then swap back (commit before, check the swap-back with a cold read). The
  actor must stop by itself, the caller gets the Last Ack, no hang, and a later Normal Stop answers 1556 (the queue is
  gone). This does NOT reach the event loop's Error frame: the producer's error sends the stop event, and the event
  loop leaves through No Error.
- **Error-frame exit** (when the step-7c shape must be proven, e.g. on existing code): commit, then set the loop VI's
  `error in` DEFAULT to an error (Actor Core leaves that input unwired, so the error enters the event loop's shift
  register and the Error frame runs on the first iteration), and swap two Merge Errors inputs so Unregister's error
  comes first. Run once: the Last Ack must carry the forced error, not 1055 from Unregister. Then restore the loop VI
  from git with the project closed and read it cold. A temporary edit of the member itself, because a throwaway copy
  of a private loop VI cannot call its private and protected callees. Measured in an evaluation, 2026-10.
- Then `ops/cleanup.md` and `ops/icons.md` for the VIs this task made.

## Report

```
(one block per helper loop)
loop <class>:<vi> variant <1|2>  events <elements>  member private static  folder Helpers <created|moved>
members: createResources createEvents init stop close <senders>  add_class_method 1 call  swaps 1 call  error case <frames>
build: generate ok  wire_dynamic_events sourceFrom <...> rightSide <...> render <ok>  specs <rows>  use-default <tunnels>  data fields <ok|n/a>
reg input: term <n> on pane <T>  init indicator: term <n> on pane <T>  init->loop wire <ends>/<broken>  error-frame refnum <ends>/<broken>
panel on call <r/r|n/a>  Stop action <1|n/a>  stop action <0|1> hidden <yes|n/a>  export <ok>  locals <n|n/a>
hooks: PLI createResources F; Actor Core init B (kept branches <n>), loop A|C, stop D, close D-close   sweep <ok>/<n>, control 0 7, membership ok
run: stop <tick> loop exit <tick> close <tick> err <code>  early stop <n>/5  producer failure <stopped|hung|n/a>
second call <ok|n/a>   unmeasured steps met: <list>
side effects: <...>   commits <hashes>   LabVIEW calls <n>   issues: <exact error text or none>
```

## Traps

- An authored refnum tunnel made `lvai_wire_dynamic_events` branch a plain tunnel, the wrong shape (pilot rule 60,
  1.8.5). labview-mcp now prefers an authored tunnel; this route still authors none, so step 5 must read `sourceFrom`
  = the diagram.
- Unregister must follow the loop by data flow (its refnum from the loop's output tunnel). Fed from the refnum control
  it runs as soon as the loop VI starts, the stop event never arrives, and every stop hangs the actor until LabVIEW is
  killed (measured in an evaluation, 2026-10).
- Merge Errors with the loop's error first hides an error from Unregister (a null refnum answers 1055): a clean run
  does not prove the registration is released.
- `lvai_add_class_method` with `aixml` and `vi` re-converts the VI: dynamic wiring, specs and data fields are lost.
- `pylv-set-event-spec.py` of labview-mcp documented a `[dynIndex]` it did not take (1.8.5): for a hand fix use the
  kit script.
- A plain AIXML convert of the loop VI loses every event frame; regenerating the loop repeats steps 3–10.
- A loop branched beside Call Parent never sees its actor stop through a failed `Send`: its only exits are the stop
  event or the local `stop`. A hung loop cannot be aborted by VI Server; only a LabVIEW restart frees it.
- The vi-generator agent is not the route for the loop VI: it is a member that calls protected AF VIs, and the agent
  knows neither steps 5–7c nor that `lvai_wire_dynamic_events`'s default closes and saves the project. It fits a plain
  function VI the loop calls (brief per `session/brief.md`).
