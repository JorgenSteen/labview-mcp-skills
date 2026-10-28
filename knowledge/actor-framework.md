# Actor Framework and LabVIEW: how it behaves

This file holds facts that are true in every project: how AF and LabVIEW behave, hazards that were measured, and
design patterns a project may choose from. It holds no conventions. The project's choices are in
`<repo>/.labview/conventions/` (templates: `conventions/defaults/`). Where a fact motivates a choice, the line says
`convention: <concern>.<rule-id>`. How labview-mcp generates AF code is in the labview-mcp docs
(`labview-actor-framework.md`), and the tool gaps are in `knowledge/labview-mcp.md`.

Evidence classes: **measured** (a timed run, with where), **documented** (NI help, NI's AF whitepaper or template
docs, or NI/AF designers on the NI forum), **observed in production** (the user's production AF code), **reasoned**
(follows from documented behaviour, not run), **unmeasured** (stated by a source, not checked).

## Call order and lifecycle

- **Launch.** `Launch Root Actor.vi` starts the top of the tree from a plain VI and returns the root's enqueuer.
  `Launch Nested Actor.vi` starts a child: the child gets its caller's enqueuer, and the caller gets the child's.
  *Evidence: documented (AF help).*
- **Pre Launch Init (PLI)** runs inside the launch call, before Launch returns. An error from PLI aborts the launch.
  References PLI obtains have the same lifetime as the actor. The base PLI does nothing. *Evidence: documented (AF
  help for Pre Launch Init.vi).*
- **PLI must not launch actors.** Calling Launch Root Actor or Launch Nested Actor from PLI hangs it. Launch from
  Actor Core or from a message instead (`convention: af-shapes.launch-owner`). *Evidence: documented (AF help).*
- **User events created in PLI outlive the launcher.** A launcher that exits right after Launch does not take them
  with it: the stop generated about 12 s later answered 0, the loop exited, and Destroy answered 0 (2 of 2 runs).
  *Evidence: measured in the pilot project (2026-09, its rule 98).*
- **Actor Core** is the message loop. An override runs its own code in parallel with Call Parent. Call Parent
  returns only when the message loop has ended and Stop Core has run.
- **Run order, measured.** PLI → Actor Core (series hooks, then branch hooks) → (a Normal Stop arrives) →
  Handle Error → Stop Core → Call Parent returns → code placed after Call Parent → the override's branches finish.
  *Evidence: measured in the pilot project (2026-09, its rule 88).*
- **Stop Core runs inside Actor Core's Call Parent,** so it runs before anything placed after Call Parent. A log line
  from Stop Core came first, in the same millisecond tick as a line from the after-Call-Parent hook. *Evidence:
  measured in the pilot project (its rule 93); documented (AristosQueue, NI forum 2016).*
- **Stop Core runs only if Actor Core started.** It does not run after a failed PLI. So a PLI that fails must release
  what it already created itself. *Evidence: documented (AristosQueue, NI forum, "Cleanup after Pre Launch Init");
  measured 2026-10-09 (skillsaudit M-CLOSE M3): a PLI returning error 5000 after its Call Parent made Launch return
  5000 with no Stop Core log line and no hang; the control run without the error logged Stop Core.*
- **PLI's own cleanup works** as a body hooked after PLI's Call Parent on class and error: create → Merge Errors → a
  case structure on the merged error, whose Error frame releases and whose No Error frame passes → `error out`.
  *Evidence: measured 2026-10-10 (an AF measurement series on throwaway actors): a body that obtained a notifier and
  then met a forced error 5004 made Launch return 5004; in the Error frame Release Notifier answered 0 and a status
  read chained after it answered 1 (the refnum was gone); no Stop Core and no Handle Error line; 2 of 2 runs. With no
  forced error the actor launched, ran and stopped normally.* Order a check after a release by its error wire:
  unchained, the status read ran first and proved nothing. (`convention: af-shapes.pli-failure-cleanup`.)
- **A create that creates nothing launches an actor that hangs at stop.** If `createResources`' create call leaves the
  events field null with no error (a wrong or swapped create, a create whose error is dropped), PLI succeeds, Launch
  answers 0 and the actor runs; Register For Events on the null refnum gives no error, the stop event can never reach
  the loop, the Last Ack times out and the actor stays in memory until LabVIEW is killed. The guard: `createResources`
  tests each created refnum with `Not A Number/Path/Refnum?` and turns an invalid one into an error merged into its
  case selector; Launch then returns that error, Actor Core never runs (no Stop Core, no Handle Error), and the
  launcher returns within its timeout. *Evidence: measured 2026-10-26 (an AF measurement series on a throwaway actor,
  the create call swapped onto a same-pane member that creates nothing): without the guard Launch 0 and a hang at
  stop; with the guard (code 5101) the forced failure gave Launch 5101 and no hang 3 of 3, and the normal launch ran
  and stopped with Last Ack 0 3 of 3.* (`convention: af-shapes.pli-failure-cleanup`.)
- **Stop Core's pane has no error in or error out,** only `final error code`, which tells whether the actor stopped
  because of an error. The base Stop Core passes the stop to every auto-stop nested actor. A child launched with
  auto-stop FALSE must be stopped by the caller's own Stop Core. AF gives Stop Core no error report because the caller
  may already be gone. *Evidence: documented (AF help for Stop Core.vi, Launch Nested Actor.vi; AristosQueue).*
  Release errors there are logged or cleared on purpose (`convention: errors.release-errors`).
- **Handle Error runs on every normal stop.** `Send Normal Stop` delivers a message whose `Do.vi` returns error 43,
  so Handle Error is called once at each stop, before Stop Core. Emergency Stop returns 1608. Outside a stop, Handle
  Error runs only when a message's `Do.vi` returned an error. *Evidence: measured in the pilot project (its rules
  27 and 88).*
- **An error wired into Actor Core's Call Parent** skips Handle Error, but Stop Core still runs and the actor stops by
  itself. The launcher sees nothing at Launch (error 0); its next `Send` to the actor fails with 1556. *Evidence:
  documented (AristosQueue 2016, CaseyM 2023, NI forum); measured 2026-10-09 (skillsaudit M-CLOSE M4, error 5001, with
  a control run where Handle Error logged 43). What Actor Core then returns was not observed: a root actor's output
  reaches no caller.*
- **Handle Last Ack Core** runs in the caller when a nested actor has stopped. Its Last Ack carries the stopped actor's
  object and its error. The base version only returns that error, so by default a child's error stops its caller,
  and the stop travels up the tree. *Evidence: documented (AF help).* (`convention: af-shapes.handle-last-ack`.)
- **Send Normal Stop** asks an actor to finish its queue and stop. Shutdown of a tree follows from it: the base Stop
  Core stops the auto-stop children. *Evidence: documented (AF help).*

## Overrides and connector panes

- **Measured panes of the AF overrides** (conIdx). An override keeps its parent's file name and pane.

  | override | pane |
  |---|---|
  | Pre Launch Init | `<C> in` 11, `<C> out` 3, `error out` 0; **no `error in`** |
  | Actor Core | `error in` 8, `<C> in` 11, `Actor out` 3, `error out` 0 |
  | Stop Core | `<C> in` 11, `<C> out` 3, `final error code` 10 |
  | Handle Error | `error in (no error)` 8, `<C> in` 11, `<C> out` 3, `error out` 0, `stop actor?` 2 |

  *Evidence: measured in the pilot project (2026-09).* The pane of `Message.lvclass:Do.vi` is in the labview-mcp
  docs, `labview-actor-framework.md` §2.
- **Actor Core's `Actor out` is typed `Actor`,** also on the Call Parent node, not the child class. A child-typed VI
  fed from it needs `To More Specific Class`. Code after Call Parent that needs the child type takes the class wire
  from before Call Parent. *Evidence: measured in the pilot project (its rule 74).* (`convention:
  af-shapes.stop-site`.)
- **PLI's Call Parent has no error input,** and the base PLI does nothing. So "in series before Call Parent" in PLI can
  only mean the class wire, and the order of work inside PLI does not change what the parent does. *Evidence:
  documented (AF help); reasoned.*
- **Error 43 on Handle Error's `error in`.** Because every normal stop arrives as 43, a VI chained on Handle Error's
  incoming error is skipped at every stop. Side work there (logging, file I/O) needs a fresh error chain. *Evidence:
  measured in the pilot project (its rule 88).*
- **The parent Handle Error** always returns `stop actor?` = T (a constant), and it clears 43 as a normal shutdown.
  Every other code is passed on, **1608 (Emergency Stop) included**, and the actor stops. So a body after Call Parent
  sees no error at a Normal Stop and 1608 at an Emergency Stop. An override that does not call the parent must clear
  43 itself. *Evidence: documented (AF help for Handle Error.vi; NI forum); NI's source (`Actor.lvclass:Handle
  Error.vi`, its case on the code clears 43 only; read 2026-10-17 for labview-mcp's AF docs); measured 2026-10-10 (an
  AF measurement series on throwaway actors): a body after Call Parent logged code 0 at a Normal Stop and 1608 at an
  Emergency Stop, 2 of 2 each, with Stop Core 0–1 ms later.*
- **Which order can keep an actor running.** A handler placed before Call Parent can log or rewrite the error, but the
  parent still returns T. Only code after Call Parent can set `stop actor?` back to F: a body on Call Parent's
  `stop actor?` and `error out` (the "third wire"; the body needs no class terminal, e.g. `error in`, `stop in` →
  `error out`, `stop out`). *Evidence: measured 2026-10-10 (the same series): `Send Error Report.vi` delivered 5003,
  the parent answered T, the body turned it to F for 5003 only, Stop Core did not run, and a Normal Stop 500 ms later
  answered 0 and stopped the actor (2 of 2); the control without the body stopped on the 5003, and the later Normal Stop
  answered 1556.* **The parent also answers T at a Normal Stop,** so the handler overrules only the codes the error
  plan names: one that always answers F makes the actor ignore its own Normal Stop. (`convention:
  af-shapes.handle-error-order`, `errors.plan-required`.)
- **Scope.** `Read Self Enqueuer.vi` is protected: a VI that is not a member of an actor class cannot call it (the
  caller is broken, error 1003). A private dynamic-dispatch member VI is broken ("error of type 2000000"), so private
  accessors are static. *Evidence: measured in the pilot project (its rules 41 and 30).*
- **A static VI inside a dynamic-dispatch recursion cycle is broken** (a static hook calls a dynamic method that can
  dispatch back to the caller). A dynamic VI that recurses directly is fine. Making the static VI shared-clone
  reentrant fixes it. *Evidence: measured in the pilot project (its rule 52).*
- **Receive Message.vi** is a protected override that sees every message before it is executed; it is the place for
  message tracing. *Evidence: documented (AF).*
- **Never graft a diagram into an override.** `lvai_graft_diagram` in place onto a `Stop Core` override (a copy of it
  as the panel VI, the override as the output, the project open) raised an untitled modal dialog ("… has changed on
  disk since last saved or loaded by LabVIEW …" [Revert] [Cancel]) instead of refusing, gave no answer within 300 s,
  and the next call, an open of the same project, ended in a fatal LabVIEW crash. The tool copies the panel VI over
  the output before its first LabVIEW step, so a loaded output VI meets a file that changed under it; and a graft that
  completed would delete Call Parent with the rest of the diagram (reasoned). Change an override's body by hooks
  (`ops/override.md`). *Evidence: measured 2026-10-10 (an AF measurement series), 1 of 1, not retried.*

## User events and helper-loop hazards

- **Destroy before Generate hangs the actor.** If Stop Core destroys a user event and code after Call Parent then
  generates the stop on it, `Generate User Event` answers error 1 (destroyed refnum). The loop never gets its stop,
  so the Actor Core override cannot return, and the actor hangs at stop. *Evidence: measured in the pilot project
  (2026-09, its rule 93); documented (error 1 on a destroyed refnum, NI forum).* (`convention: af-shapes.close-vi`.)
- **Generate, then Destroy, does not lose the event.** A destroy placed right after the generate (0–1 ms later, both
  error 0) still let the loop exit, and the actor stopped in 4 of 4 runs. NI R&D states the same: destroying a user
  event stops new generates, but events already queued still fire. The LabVIEW 2020 help for Destroy User Event says
  the opposite; the newer R&D statements and the measurement agree. *Evidence: measured in the pilot project (its
  rule 97); documented (justACS 2016, Darren 2023, NI forum).* The same holds when both the generate and the destroy
  sit in Stop Core. *Evidence: documented (NI forum); observed in production code, where several actors do exactly
  that; measured 2026-10-10 (an AF measurement series): a body after Stop Core's Call Parent doing Generate, then
  Destroy chained on the Generate's error (both error 0), ended the helper loop in the same millisecond, 3 of 3, and
  the actor stopped.* **One stop site per actor:** the same actor also kept a stop after Actor Core's Call Parent, and
  that Generate then answered error 1 on the destroyed refnum each time.
- **`close` after the joined error wires works.** Actor Core: the helper loop beside Call Parent; after Call Parent the
  stop hook on a fresh chain; Merge Errors(loop `error out`, stop hook `error out`) → `close` (Destroy User Event);
  Merge Errors(Call Parent `error out`, `close` `error out`) → Actor Core `error out`. In 5 of 5 runs (four with a
  launcher that stops the actor after 1 s, one with a launcher that exits at once and a stop ~16 s later) `close` ran
  7–112 ms after both the loop's exit and the stop, error 0, the actor stopped, no hang. *Evidence: measured
  2026-10-09 (skillsaudit `measure/PB-CLOSE`, run/close_M1.txt).* (`convention: af-shapes.close-vi`.)
- **A hung helper loop cannot be freed by VI Server.** Abort VI on it answers error 1000, and Callers' Names returns
  the original `Actor Core.vi`, not the running clone. Only a LabVIEW restart frees it. *Evidence: measured in the
  pilot project (its rule 94).*
- **A failed `Send` does not stop a helper loop.** The actor's queue lives until the Actor Core override returns, so a
  loop branched beside Call Parent never sees its actor stop through a failed send to itself. It needs its own stop
  signal: a user event, a notifier, a local variable or a stop element. Never abort it. *Evidence: measured in the
  pilot project (its rule 21).* (`convention: af-shapes.stop-mechanism`.)
- **A notifier stop costs about one loop period.** A polled loop with a 200 ms tick that checks `Wait on Notification`
  (timeout 0) each iteration exited 215–313 ms after Stop Core fired the notifier. Obtain the notifier in a PLI body
  after Call Parent, error wired, so a failed obtain fails the launch; where the obtain sits does not change the stop
  timing. *Evidence: measured 2026-09 (an AF measurement series on a two-actor tree).*
- **A UI loop needs both exits:** on its Stop button it sends Normal Stop to its own actor, and it also exits on the
  stop signal, so the button and an external Normal Stop both end the tree. Log a loop's exit from data that leaves
  the loop through a tunnel: a log node fed from a constant runs at the start, beside the loop. *Evidence: measured 2026-09 (the same
  two-actor series).*
- **Register For Events skips on an upstream error.** It has standard error-in behaviour: with an error in, it does not
  run and nothing is registered. The event structure then waits for events that never come, and a loop whose only
  exit is the stop event hangs the actor at stop. *Evidence: documented (LabVIEW help for Register For Events);
  the hang is reasoned (the pilot project's rule 73).* (`convention: af-shapes.registration`.)
- **Generating an event nobody registered for does nothing,** with no error. So a stop sent to a loop that never
  registered (for example one that returned at once on an error) is harmless, and it cannot rescue such a loop.
  *Evidence: documented (LabVIEW help for Generate User Event).*
- **Events generated before Register are not seen, and that hangs a tree.** Registration starts queuing from the
  moment Register runs; a stop generated before it is lost. With Register inside the loop VI, a Call Parent that
  returns at once (an error wired into it, e.g. a failed nested launch in the root) lets the stop hook generate the
  stop before the loop has registered: the loop never exits, `close` never runs, Actor Core never returns, no Last Ack
  reaches the caller, Normal Stop answers 0 and changes nothing, and the tree stays in memory until LabVIEW restarts.
  Registering in an `init` member in series before Call Parent fixes it. *Evidence: documented (LabVIEW help); measured
  in a harness run, 2026-10: the failing launch hung the tree with Register in the loop VI, and with `init` the same
  run passed (Last Ack in 70 ms carrying the real error), early stop 5 of 5 with no hang on two actors.*
  (`convention: af-shapes.registration`.)
- **Destroy on an already destroyed user event answered error 0** in 5 of 5 runs (the loop VI had destroyed the events
  and `close` destroyed them again). *Evidence: measured indirectly, 2026-10-09 (skillsaudit M-CLOSE M1).* Do not build
  on it; destroy each event in one place.
- **Error behaviour of the event nodes.** Generate User Event skips on an incoming error. Destroy User Event and
  Unregister For Events run even with an error in, so both are safe at the end of an error chain. *Evidence:
  documented (LabVIEW help).*
- **Unregister.** Registrations end when the VI that registered finishes or is aborted. NI still recommends
  Unregister: until then, events keep queuing for the registration. *Evidence: documented (LabVIEW help).*
- **Register For Events takes a cluster.** Wired to one event source, a cluster (or array) of user-event refnums
  registers every element. *Evidence: documented (LabVIEW help); measured to compile in the pilot project (its rule
  66). Only the form with one event source per element (Unbundle By Name) was run there.* Event-case selectors then
  use the element's label.
- **A local variable works only inside the VI that owns the control.** Loops that share a local `stop` must sit in one
  VI. *Evidence: documented LabVIEW behaviour.* (`convention: af-shapes.stop-mechanism`.)
- **An off-pane control keeps its last value** between calls, as long as the VI stays in memory. A `stop` Boolean read
  through a local must be written F before the loops start, or a second run stops at once. A test of that reset calls
  the VI twice from one caller: two separate top-level runs unload the VI in between and test nothing. *Evidence:
  measured in the pilot project (its rule 63).*
- **A local-variable read with no data dependency runs at the start of the iteration,** in parallel with `Wait (ms)`.
  A stop through that local then costs up to two intervals (121 and 123 ms at 100 ms). Read after the Wait, it cost
  17–22 ms. *Evidence: measured in the pilot project (its rule 61).*
- **Timeout frame.** LabVIEW requires a Timeout case only when the Timeout terminal is wired; -1 means never. The
  Timeout case fires only when no event has come for the whole timeout, so a steady stream of events starves it. A
  0 ms timeout makes the loop spin whenever the queue is empty. *Evidence: documented (LabVIEW help, NI forum); the
  busy loop is reasoned.* (`convention: af-shapes.timed-work`.) The pilot's "an event structure with only user-event
  frames needs a Timeout frame" is a labview-mcp build-step limit, not LabVIEW: see `knowledge/labview-mcp.md`.
- **Front-panel Booleans and VI Server.** A value written by VI Server (`Value`, `Ctrl Val.Set`) fires no Value Change
  event; only `Value (Signaling)` does. A latched Boolean cannot be written by VI Server at all (error 1193), so a
  latched Stop in an event structure can only be pressed by a person. A button a test must press is "Switch When
  Released", reset to F by a local in its own frame. *Evidence: measured in the pilot project (its rule 35).*
- **A refnum lives as long as the VI hierarchy that created it,** so events created in Actor Core are released when the
  actor ends. *Evidence: documented (NI AF whitepaper).*

## Errors in AF

- **Default propagation.** An error from a message stops the actor (Handle Error returns T). The actor's Last Ack
  carries the error to the caller, whose Handle Last Ack Core returns it, so the caller stops too. *Evidence:
  documented (AF help; AristosQueue).* (`convention: errors.default-policy`.)
- **Errors in Actor Core's own code never reach Handle Error.** That covers the override's diagram and the helper loops.
  They reach it only when sent: `Send Error Report.vi` delivers an error to an actor's Handle Error, and if it is not
  handled there it stops that actor. *Evidence: documented (AF help for Send Error Report.vi; AristosQueue).*
  (`convention: errors.loop-errors`.)
- **Errors before the actor runs** (in PLI) are not Handle Error's business: they abort the launch, and the launcher
  sees them. *Evidence: documented (AF help; AristosQueue, LAVA).*
- **`Clear Errors.vi` in LabVIEW 2026 has `specific error code to clear (0: all)`.** With a code it clears only that
  code. Clearing a list of codes (say 56 and 66) needs a Case on the code with a no-error constant in those frames.
  *Evidence: measured in the pilot project (its rule 55). Older LabVIEW versions: unmeasured.* (`convention:
  errors.ignored-errors`.)
- **UDP on Windows** (met in an AF communication actor). `UDP Write` to a port nobody listens on, or to an unreachable
  IP, returns no error. The next `UDP Read` on that socket returns 66 at once (the ICMP reset). A read with no
  datagram returns 56 (timeout). *Evidence: measured in the pilot project (its rule 43).*

## Messages

- **A message** is a class that inherits from `Message.lvclass`. It carries its payload in its private data, and its
  `Do.vi` override calls one method of the actor. `Send <method>.vi` bundles the payload and enqueues it.
  *Evidence: documented (AF).*
- **NI's Message Maker** ("Create Messages for Actor") generates the message class, its `Do.vi` and its `Send` VI from
  an actor method; nobody writes `Do.vi` by hand. The payload is every input of the method other than the class and
  the error cluster, one private field each, in descending conIdx. Details and the labview-mcp route: labview-mcp
  docs, `labview-actor-framework.md` §2, §4, §11a, §13a. (`convention: af-shapes.messages`.)
- **A custom parent between the messages and `Message.lvclass`** changes what Message Maker generates. *Evidence:
  unmeasured (a caution recorded by the pilot, its rule 5).* Measure before introducing one.
- **Drop Message Core.vi** runs on a message that is discarded because its actor is stopping. Its use is a message
  that hands over ownership of a reference, so the reference is not leaked at shutdown. A message that only carries a
  reference its owner closes needs no override. *Evidence: documented (AristosQueue 2013, NI forum); observed in
  production code (no override in its messages, by design).*
- **Time-Delayed Send Message.vi** sends a message later, once or repeatedly. NI's AF template does periodic work with
  it and stops it in Stop Core. *Evidence: documented (NI AF template docs).*
- **JSON in payloads.** `Flatten To JSON` refuses an enum ("type is invalid"), even inside a cluster. `Unflatten From
  JSON` matches by field name and ignores extra members when strict is F. *Evidence: measured in the pilot project
  (its rule 45).*

## Libraries as load units

- **A LabVIEW library is a load unit, not only a namespace.** Loading any member loads the `.lvlib`, and a loaded
  library brings in every class and sub-library it contains, with their member VIs and dependencies. *Evidence:
  documented LabVIEW loading behaviour; not measured in the pilot.*
- **Consequence.** If an abstract parent and all its concrete children share one library, a caller that uses only the
  parent still loads every child and each child's toolkits (an MQTT child pulls in its MQTT toolkit). The code-level
  rule "the manager references only the parent" can hold while the load-level dependency drags the children along.
- **Pluggable children** each get their own library that depends on the parent's library. Then only the code that
  constructs a child loads it. A class can also stand alone, outside any library. (`convention:
  layout.library-per-actor`.)

## Design patterns (a menu; the project picks)

None of these is required by AF. A project chooses, and the choice is recorded in its conventions (`convention:
af-shapes.one-pattern-per-area`). NI recommends one data-transfer mechanism per actor and few across the application.
*Evidence: documented (NI AF whitepaper).*

- **Tree shape.** One root, a layer of managers that each own a subsystem, leaves that do one thing; three or four
  launch levels. A launcher VI does Launch Root Actor, then waits, then Send Normal Stop (or the root stops itself).
  Leaves come in kinds: panels (a helper loop on user events), workers (a blocking read or DAQ loop that forwards each
  item to the caller), minions (stateless set/get). (`convention: af-shapes.tree-shape`.)
- **Launch on request.** A panel is launched when asked for and reports back when it closes; the manager keeps a status
  table.
- **Deferred start.** PLI sends an `init` message to self, or Actor Core calls an `init` method; the children are
  launched from there. Sending the launch message from PLI is a launch from a message: the launch itself runs in the
  message's `Do.vi`, once Actor Core's loop handles it. An `init` member in series before Call Parent
  (`af-shapes.registration`) launches before the caller's message loop runs: messages a child sends meanwhile wait in
  the caller's queue and are handled once Call Parent's loop starts. *Evidence: measured in a harness run, 2026-10 (a
  root launching two children from `init`).*
  - **A PLI body that sends the launch message must sit after Call Parent with its error wired** to PLI's `error out`
    (`Read Self Enqueuer` → `Send <launch>`; `Read Self Enqueuer` is protected, so the body is a class member). A
    branch body wires the class only, so a failed send is seen by nothing. *Evidence: measured 2026-10-10 (an AF
    measurement series): a body after Call Parent whose `Send` went to an enqueuer with no queue behind it made Launch
    return 1556, and the actor never ran (no Handle Error, no Stop Core), 2 of 2; the control body launched with 0 and
    the actor handled the message once Actor Core ran. The branch form started the child with nothing sent by the
    launcher (the 2026-09 two-actor series), its send error unobserved.*
- **Base actor or direct `Actor`.** AF's reuse model is inheritance: a base actor carries shared overrides, and a child
  decorates them (e.g. adds a loop to Actor Core). A base can offer an empty dynamic hook that its Stop Core calls, so
  a leaf overrides the hook, not Stop Core. Two or three base levels are normal; NI's own samples use them.
  *Evidence: documented (NI AF whitepaper and samples).* (`convention: af-shapes.base-actor`.)
- **Talking up: interfaces or abstract messages.** The caller knows its children's classes; a child knows only `Actor`,
  its own messages, and an interface or abstract message for talking up. An abstract message lives in the child's
  library with `Send` but no `Do.vi`; the caller supplies a child class with the `Do.vi`. With an interface, the
  child's message calls an interface method the caller implements. NI prefers interfaces since LabVIEW 2020 and calls
  abstract messages "not recommended for any new development". A child written for exactly one caller ("high
  coupling") is a named option. A violation shows as a child's library referencing its caller's `Send` VIs.
  *Evidence: documented (NI AF whitepaper).* (`convention: af-shapes.dependency-direction`.)
- **Cross-tree talk.** NI recommends talking only to the caller and the nested actors, with a stated exception for
  performance (e.g. a sibling handed an enqueuer for a data stream; the caller then owns both lifetimes). *Evidence:
  documented (NI AF template docs; NI forum).*
- **Typed payload hierarchy.** A few generic messages carry a payload class hierarchy. The payload parent holds a type
  tag, a timestamp and any cleanup; children add the data. New data types need no new messages.
- **Message router.** Children of one abstract message parent are chosen at run time from a payload-class →
  message-class table built in PLI. The data type becomes method dispatch, with no string case structure.
- **Periodic work.** Three forms: a time-delayed message to self (NI's template), a timed loop in the helper-loop VI
  stopped by a local, or a Timeout frame. The Timeout frame gives no guaranteed rate and starves under event load.
  *Evidence: documented (NI template; drjdpowell, LAVA).* (`convention: af-shapes.timed-work`.)
- **Stop mechanism for a helper loop.** A user event into the event structure, a notifier, a stop element in a queue,
  or a local variable (for loops in the same VI). All are valid; never abort a loop.
- **Where the stop is sent.** Two working forms. (1) Generate the stop and then destroy the event, both in Stop
  Core: NI's whitepaper form, documented and observed in production code. (2) Send the stop in Actor Core after Call Parent,
  with the release after it: measured in the pilot. Form 2 sees every exit of Call Parent in one VI. It is safe only
  if its Generate is not chained on Call Parent's error (it would be skipped) and nothing it needs was released in
  Stop Core. (`convention: af-shapes.stop-site`, `af-shapes.close-vi`.)
- **Shutdown cascade.** `Send Normal Stop` from the root downward (the base Stop Core does this for auto-stop
  children); a request to stop the application travels upward as a message; the root stops last. (`convention:
  af-shapes.shutdown-cascade`.)
- **Supervision.** The caller overrides Handle Last Ack Core to read the stopped child's error, classify it, and
  relaunch or update a status table. Without it, the default propagation stops the caller.
- **Instrumentation left in.** A `Receive Message.vi` override that logs every message class name, inside a disabled
  frame.

## Observing and testing actors

- **Any member VI of an actor class can be run directly,** without launching the actor. *Evidence: documented (NI AF
  whitepaper).*
- **`Execution:State` read from inside a launcher is not a stop detector:** a reserved VI reads 3 (running). Prove a
  stop by timestamped log lines, `error out`, a Normal Stop to the caller that succeeds, and a state read after the run
  with nothing loaded. *Evidence: measured in the pilot project (its rule 31).*
- **Two VIs appending to one log file at the same moment** overwrite each other's line (same offset). In runs that
  prove an order, give each writer its own log file, and take the timestamp at the write. *Evidence: measured in the
  pilot project (its rule 98).*
- **A tree can be proved without a throwaway caller class.** The proof VI launches the top actor with AF's public
  `Launch Actor.vi`, with a proof-owned message queue as its caller, and each child with `Launch Actor.vi` and its
  real parent's enqueuer as the caller. The proof queue receives the top actor's Last Ack (its error is the cascade
  code); a later Normal Stop answering 1556 shows the actor had already stopped by itself. *Evidence: measured in
  a harness run, 2026-10.*
- **A child's error cascades up through the Last Ack:** a child stopping with error 5000 sent its Last Ack, and the
  caller and the whole tree stopped by themselves 0.56–0.64 s after launch (AF's default Handle Last Ack Core). A
  root whose nested launch failed in its `init` returned its Last Ack in 70 ms carrying that nested error.
  *Evidence: measured in a harness run, 2026-10.*

## Not yet measured

Open questions. They are not decided, and nothing in the skill may assume an answer.

- **What Actor Core returns after an error into its Call Parent,** beyond the Last Ack: the Last Ack carried the
  error in the measured cases ("Observing and testing actors"); Actor Core's own `error out` was not read.
- **The Stop Core release order** was an open proposal (AP-4, DR-6), settled by the user on 2026-10-09 as a convention
  (`convention: af-shapes.stop-core-order`); an order between several releases has not been run. (PLI failure
  cleanup was settled the same day and has been measured since: "Call order and lifecycle". Settled too: the
  parent passes 1608 on, "Overrides and connector panes".)
- **What makes an early stop safe beyond `init`:** with the stop sent after Actor Core's Call Parent and Register
  inside the loop VI, a Normal Stop sent right after Launch was generated before the loop registered (the loop's
  first node ran 38 ms later) and the actor hung (an AF measurement series, 2026-10-10, 1 of 1). Registering in `init`
  before Call Parent is the measured fix ("User events and helper-loop hazards"); other forms (a "registered" signal, a
  polled stop) are unmeasured.
- **`Clear Errors.vi` in older LabVIEW versions** (e.g. 2020): whether `specific error code to clear` exists there.
- **Handle Last Ack Core with a body:** its pane is read (`ops/override.md`, shape H); no body on it has been run.
