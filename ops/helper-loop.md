# Helper loop: build an actor's loop VI and wire it into Actor Core

**When:** a task adds a helper loop to an actor (a UI or panel loop, an acquisition or producer loop, a loop on user
events), adds user events for one, or changes how a loop is registered or stopped.

**What it gives:** the events typedef and its field, the role members (`createEvents`, `stop`, `close`, senders), the
loop VI as a private class member with the registration wired through the event structure's dynamic terminal, the
hooks on Pre Launch Init and Actor Core, every member executable cold, and a run in which the actor stops cleanly.

**Not here:** creating the overrides and each helper's inputs for a hook (`ops/override.md`, shapes A, B-after, D,
D-close); the events field route (`ops/class-field.md`, route A); a new actor class (the class-generator agent, below);
how AF and user events behave (`knowledge/actor-framework.md`, "User events and helper-loop hazards"). In local mode,
or when a concern is off, follow the surrounding code instead.

## Before you start

- **Setup level:** a new loop is level 4 (af-shapes, naming, layout, errors). Conventions used:
  `af-shapes.one-pattern-per-area`, `af-shapes.helper-loop-vi`, `af-shapes.helper-loop-error-case`,
  `af-shapes.registration`, `af-shapes.stop-mechanism`, `af-shapes.stop-site`, `af-shapes.close-vi`,
  `af-shapes.timed-work`, `af-shapes.events-typedef`, `af-shapes.global-events`, `af-shapes.resources`,
  `naming.role-names`, `naming.method-case`, `layout.class-folders`, `layout.scope`, `layout.accessors-on-demand`,
  `errors.loop-errors`, `errors.ignored-errors`.
- **Maintenance scope.** An existing actor keeps its loop, stop and teardown shape (for example a Stop Core that
  generates and destroys) unless the task is to change it. A second loop in that actor follows its first loop.
- **The actor class exists.** A new one comes from labview-mcp's class-generator agent, briefed per
  `session/brief.md` with the parent `vi.lib\ActorFramework\Actor\Actor.lvclass`, the `events` and
  `prelaunchSettings` fields, "make only the accessors `Read events`, `Write events`, static, private" (or none yet),
  and the folder, naming and scope rules from that file's table; check it afterwards as that file says.
- **The kind of loop** (`convention: af-shapes.stop-mechanism`): every loop VI has at least one loop on an async stop
  (a user event by default). Variant 1 is that event loop alone; variant 2 adds other loops (timed producer, polling)
  in the same VI, stopped by the local `stop` the event loop sets. A polling-only loop VI therefore gets an event loop
  too. A notifier or queue instead of the user event is allowed by the convention but not measured here.
- **Build order, project state, commits:** `knowledge/labview-mcp.md`, "Evidence, git, build order" and "Project open
  or closed, per kind of call". Commit before each structural step (typedef, field, each member, the loop, each hook).

## Steps

1. **Events typedef and field** (`convention: af-shapes.events-typedef`): `ops/class-field.md`, route A. Type
   spelling e.g. `cluster{ref{UserEvent}{bool.stop}.stop,ref{UserEvent}{string.error}.error}`; the suffix labels the
   element, which the event frames select (`knowledge/labview-mcp.md`, "lvai_create_typedef ..."). Make `Read
   events` and `Write events` only when step 2 uses them. Global events: `convention: af-shapes.global-events`.
   > MCP-candidate: user-event-cluster
2. **Role members:** `createEvents`, `init`, `stop`, `close` and any sender, named per `convention: naming.role-names`;
   their content per `af-shapes.events-typedef`, `af-shapes.registration`, `af-shapes.stop-site`, `af-shapes.close-vi`,
   `af-shapes.resources`. `init`: `Read events` on a fresh error chain → `Unbundle By Name` → `Register For Events`
   on a fresh "no error" constant, its refnum output left unwired (step 11 puts it on the pane); `error out` = Merge
   Errors (`error in`, `Read events`' error, Register's error); for a root that launches nested actors, the launches
   too (as subVIs).
   Author each in AIXML with the class as a `path` stand-in and the accessors as `lvai_placeholder_subvi` stubs.
   Then **one** `lvai_add_class_method` call for all of them (`methodsJson` entries with `aixml` and `vi`,
   `classTerminals` = `["<C> in"]`, no `dispatchTerminals` = static; `projectPath`), and **one** `lvai_swap_subvis`
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
     steps 5 and 6.
   - **The error case, inside the loop** (`convention: af-shapes.helper-loop-error-case`): `error in` enters the loop in
     a shift register; a `<Structure _name="Case Structure">` with `selectin` = that error. Error frame: the loop's stop
     terminal T, the error passed on. No Error frame: the event structure (or the loop's work). The AIXML reference
     lists error-cluster selectors (`No Error`, `Error 1..5`, `Default`). Every output tunnel needs a value in both
     frames (the refnum tunnel step 5 creates is the exception: step 7 sets it). Built and run in a harness run
     (2026-10, state 1 after steps 5–7).
   - Frames select the element label, e.g. ` <stop>\3A User Event `. Timeout frame per `convention:
     af-shapes.timed-work`; an event structure whose frames are all user events needs an empty one for step 7.
   - Sends to its own actor: `Read Self Enqueuer` → a generated `Send <method>.vi` (protected: the VI must be a member).
     Loop errors per `convention: errors.loop-errors` (measured: the project's error method, then `Send Normal Stop`
     to self).
   - Variant 2: one VI, the locals by `<Node _name="Local Variable" element="stop" .../>` (`inputs=` writes,
     `outputs=` reads); `stop` written F before the loops (`af-shapes.stop-mechanism`); the producer's read of `stop`
     sequenced after its `Wait (ms)` (unsequenced it costs up to two intervals: `knowledge/actor-framework.md`);
     after each non-event loop, a Flat Sequence with the actor's `stop` member → `Clear Errors` on its error, so a
     loop that ends on an error stops the event loop too.
   - `kit/example_helper_loop.xml` is an older body with a notifier exit: copy spellings from it, not its stop shape.
4. **Generate**, project closed: `lvai_generate_vi_with_events(aiXmlFilePath, viPath = <member path>)`. `ok:false` and
   state 0 are expected until step 9. It refuses two event structures in one document. Whether it keeps an event
   structure nested in a case frame inside the loop is unmeasured. > MCP-candidate: generate-with-events-fixes
5. **Both sides of the registration**, project open and active (the VI is not a member yet; the `.lvproj` lists it
   loose until step 9): `kit/pa_wire_dyn_deep.xml` (`VI Path`, capitals as written). It finds the event structure up
   to three levels down (loop → case frame → event structure, the error-case shape), wires Register's refnum output to
   the dynamic terminal and the right-side terminal to Unregister on the top-level diagram. Read `event structure
   found`, `left terminal found`, `right terminal found`, `register found`, `unregister found` T, `left wire ends` and
   `right wire ends` 2, `left wire broken` and `right wire broken` F, error 0. Measured 2026-10 on the error-case shape.
   `lvai_wire_dynamic_events` searches two levels only: here it answers Error 91 / `helperDidNotAnswer` and changes
   nothing. The new right-side tunnel has no value in the Error frame and breaks the VI until step 7.
   > MCP-candidate: wire-dynamic-events-fix
6. **One-level shapes only** (event structure directly in the top-level loop, no error case): left side
   `lvai_wire_dynamic_events(viPath, finishUserEvents: false)` (expected `sourceFrom diagram`, `wireEndsAfter 2`,
   Error 91 / `helperDidNotAnswer`; the default `finishUserEvents` closes and saves the active project), right side
   `kit/pa_wire_dyn_right.xml` (`VI Path`): `event structure found`, `dyn out found`, `unregister found` T, `wire ends
   after` 2, `wire broken` F. (pilot rule 60)
7. **User-event specs**, project closed: `pylv_extract` → `python <skill>/kit/set_user_event_specs.py <bundle> <base>
   <diagramIdx>:<element label>:<dynIndex> ...` → `pylv_rebuild`. `diagramIdx` = the frame's position in the document
   (Timeout included), `dynIndex` = the source's 1-based position on Register. Run `--check` before (current rows) and
   after. Needed for one event too. Measured rows: `0:error:2 2:stop:1`, `1:stop_event:1`. (pilot rules 39, 60)
   In the same round trip, after step 5: `python <skill>/kit/set_use_default.py <bundle> <base> --check` must list
   only the new refnum tunnel (it flags EVERY case output tunnel left unwired in a frame, which in hand-built code can
   hide a real missing wire); then run it without `--check`. It sets "Use Default if Unwired", which AIXML refuses
   ("Invalid property"). Measured 2026-10: cold state 1 with the flag, 0 without. > MCP-candidate: wire-dynamic-events-fix
7b. **Registration refnum as an input** (`convention: af-shapes.registration`), project open and active, edited in
   place: `kit/pa_reg_to_control.xml` (`VI Path`, `term index` = a free connector-pane slot, measured 10). It creates
   a control on Register's refnum input (typed like the registration), deletes Register, its Unbundle and the fresh
   constant (another consumer of the Unbundle is reconnected), wires the control to the loop tunnel Register fed, and
   puts it on the pane. Read `register count` 1, `new wire ends` 2, `new wire broken` F, `on pane` T, every error 0.
   `Read events` stays when its error feeds the loop; Unregister's `error in` is then unwired (no error). Re-check
   step 7 offline afterwards: the spec rows and the use-default flag are unchanged (measured). It runs no Remove Bad
   Wires on purpose (that would remove the inner refnum chain before the new wire exists). Measured on a throwaway,
   then on a member, 2026-10: state 1.
8. **Event data**, project closed, only for a frame that reads its payload: `lvai_set_event_data_fields(viPath,
   fields="<dataNodeUid> <placeholderUid>:4")`. `ok:false` before membership is expected.
9. **Membership:** `lvai_add_class_method` with the **existing VI only** (`methodsJson`
   `[{"vi": "<member path>", "classTerminals": ["<C> in"]}]`, `projectPath`). With `aixml` as well it re-converts the
   VI and steps 5–8 (7b included) are lost. Then `lvai_swap_subvis` the stubs; scope private (`kit/set_scope.py`, project closed);
   the folder `Helpers` (`convention: layout.class-folders`): `kit/pa_class_folder_create_and_move.xml`, or
   `pa_class_folder_move.xml` when the folder exists (project open and active; no question needed). (pilot rule 91)
   > MCP-candidate: add-class-method-rerun, move-to-folder
10. **Panel and controls** (`knowledge/labview-mcp.md`, "LabVIEW scripting quirks", panel flags and mechanical action):
    - a loop with a user-facing panel only: `kit/pa_set_panel_on_call.xml` (project open and active), read back cold
      with `kit/pa_read_panel_on_call.xml`; re-apply after any regeneration;
    - a Stop button a test must press: Switch When Released, reset to F by a local in its own frame (author the local
      in AIXML), then `kit/pa_set_mechanical_action.xml` (`mechanical action` 1, project closed);
    - variant 2's `stop`: off the pane, a switch, hidden with `kit/pa_set_control_visible.xml` (project closed); prove
      action and visibility with `kit/pa_read_boolean.xml` cold (the export shows neither).
    > MCP-candidate: control-property-setters
11. **Wire it into the overrides**, each hook by `ops/override.md`, commit and `pa_save_member` as that file says:
    - Pre Launch Init: `createEvents` is called by `createResources`, the one Pre Launch Init hook (shape F in
      `ops/override.md`), so a failed create fails the launch and is cleaned up. An actor whose only resources are its
      events may hook `createEvents` itself as shape B-after (measured), but then nothing cleans up a partial create.
    - `init` first, project open and active: `kit/pa_reg_indicator.xml` (`VI Path` = `init`, `term index` = a free
      output slot, measured 2) creates the refnum indicator on Register's output and puts it on the pane (`on pane` T,
      errors 0); then `pa_save_member`, and scope private (`kit/set_scope.py`, project closed).
    - Actor Core, in this order: the loop as shape A from `<C> in` (or C after a series hook); the `stop` hook as
      shape D (`source terminal name` = `<C> in` finds the loop's node on that wire); then shape D-close with
      `close vi path` = `close`, `loop vi regex` = the loop VI's name, `stop vi regex` = the stop hook's name.
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
  loop output tunnel, no refnum `<Tunnel>` on the event structure; variant 2 lists its locals (init write, event-loop
  write, producer read). `python <skill>/kit/vi_nets.py <vi>` shows the dynamic terminal's wire offline.
- Export Actor Core: `init` (`<C> in`, `error in`) → Call Parent (`Actor in` = `init`'s `<C> out`, `error in` =
  `init`'s error); the loop takes `<C> in` from the panel and the refnum from `init`; then the D-close shape
  (`ops/override.md`, "Checks").
- **Early stop ×5:** launch the actor and send Normal Stop right after launch (the run VI with its run time 0), five
  times: every stop code 0, the caller gets the Last Ack each time, no hang, the loop and Actor Core read 1 cold
  afterwards. For a root, also make a nested launch fail on purpose: the root must stop by itself and its Last Ack
  must carry the nested error. Measured 2026-10 on two actors, 5 of 5 each (`knowledge/actor-framework.md`).
- Run (`ops/run-checks.md`) with timestamped lines, each writer its own file (`knowledge/actor-framework.md`,
  "Observing and testing actors"): the stop line, the loop's exit, then `close` after both. Measured: `close` 20–112 ms
  after the later of the two, error 0, 5 of 5, one of them with a launcher that exits at once and a stop ~16 s later
  (M-CLOSE M1). Actor Core and the loop read 1 cold after the run.
- Variant 2: test the `stop` reset by calling the loop VI twice from one caller (two tool runs unload it in between).
- Variant 2: make the producer fail on purpose (e.g. a stub that returns an error): the actor must stop by itself,
  the caller gets the Last Ack, no hang, and a later Normal Stop answers 1556 (the queue is gone).
- Then `ops/cleanup.md` and `ops/icons.md` for the VIs this task made.

## Report

```
(one block per helper loop)
loop <class>:<vi> variant <1|2>  events <elements>  member private static  folder <Helpers|asked>
members: createEvents stop close <senders>  add_class_method 1 call  swaps 1 call  error case <frames as exported>
build: generate ok  left wireEndsAfter <n> (91 expected)  right ends <n> broken <F>  specs <rows>  data fields <ok|n/a>
panel on call <r/r|n/a>  Stop action <1|n/a>  stop hidden <yes|n/a>  export <ok>  locals <n|n/a>
hooks: PLI createEvents B-after; Actor Core loop A|C, stop D, close D-close   sweep <ok>/<n>, control 0 7, membership ok
run: stop <tick> loop exit <tick> close <tick> err <code>  second call <ok|n/a>   unmeasured steps met: <list>
side effects: <...>   commits <hashes>   LabVIEW calls <n>   issues: <exact error text or none>
```

## Traps

- An authored refnum tunnel makes `lvai_wire_dynamic_events` branch a plain tunnel, the wrong shape. (pilot rule 60)
- `lvai_add_class_method` with `aixml` and `vi` re-converts the VI: dynamic wiring, specs and data fields are lost.
- `pylv-set-event-spec.py` of labview-mcp documents a `[dynIndex]` it does not take: use the kit script.
- A plain AIXML convert of the loop VI loses every event frame; regenerating the loop repeats steps 3–10.
- A loop branched beside Call Parent never sees its actor stop through a failed `Send`: its only exits are the stop
  event or the local `stop`. A hung loop cannot be aborted by VI Server; only a LabVIEW restart frees it.
- The vi-generator agent is not the route for the loop VI: it is a member that calls protected AF VIs, and the agent
  knows neither steps 6–7 nor that `lvai_wire_dynamic_events`'s default closes and saves the project. It fits a plain
  function VI the loop calls (brief per `session/brief.md`).
