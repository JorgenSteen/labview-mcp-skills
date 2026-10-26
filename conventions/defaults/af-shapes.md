# Convention: af-shapes
status: in force
written: (setup fills in the date)

> Default template for Actor Framework code. `conventions/setup.md` copies it into
> `<repo>/.labview/conventions/af-shapes.md` and settles each rule. In an existing project, the shapes the analysis
> found win, and inside existing code the local pattern wins. Role names (`createEvents`, `stop`, `close`, the
> loop VI, the typedefs) are in `naming.role-names`. How AF itself behaves is in `knowledge/actor-framework.md`;
> these rules build on it.

## one-pattern-per-area
Once an area of the code (a deployable tree, a subsystem) solves a concern one way, every actor in that area solves
it the same way. The concerns are: helper loop, stop, events, errors, launch, messaging. A new actor in an existing
area follows that area's shape. A major change that would introduce a second shape is asked about before building.
A deliberate deviation is recorded in `decisions.md`.
source: default

## architecture-by-user
The class hierarchy, base actors and the actor tree of a new build are the user's call. Propose them, then ask.
source: default

## base-actor
A base actor (carrying shared overrides, methods and messages) is used only where a family shares real behaviour,
e.g. GUI panels with many common features. Actors that share little inherit `Actor` directly. When unsure, ask.
source: default

## tree-shape
One root, a layer of managers that each own a subsystem, and leaves that do one thing. Three to four launch levels,
rarely more.
source: default

## launch-owner
An actor launches what it owns: a panel its graphs, a hardware manager its hardware actors, a communication manager
its communication actors, the root the main parts. Each launch is a method of the caller (`prelaunch-settings`),
called from Actor Core (the `init` member before Call Parent, `registration`) or from a message, never from Pre
Launch Init (a Pre Launch Init body may SEND the launch message to self: that is a launch from a message). A child launched from `init` may send before the caller's message loop runs; its messages wait in the
caller's queue until Call Parent's loop starts. Launch on request (e.g. a panel when it is asked for) where it fits.
source: default

## dependency-direction
Dependencies point one way: a caller may depend on its children (use their `Send` VIs and types); a child never
depends on its caller. A child talks up through an interface (or an abstract message) by default. A direct `Send`
to the caller is accepted for a leaf with exactly one possible caller, or one that depends on it anyway.
source: default

## shutdown-cascade
Shutdown runs as a cascade of `Send Normal Stop` from the root downward. A request to stop the application travels
upward (panel → manager → root) as a message. The root stops last.
source: default

## prelaunch-settings
Every actor has ONE pre-launch settings typedef holding everything it needs at launch: configuration, references,
the global events, and so on. Pre Launch Init reads it and creates the actor's resources from it.
- **The actor's own class owns the typedef and its write accessor.** Both are members of the class, not of the
  caller.
- **The accessor is a custom one, `writePrelaunchSettings`,** made public because the caller calls it. Its settings
  input is required. Its class input is optional: unwired, it writes into a default object of the class.
- **The caller launches the child in a launch method of its own** (`naming.role-names`, e.g. `launchHwm` in the
  root): fill the settings → `writePrelaunchSettings` → Launch Nested Actor.
Why: the typedef documents what the actor requires, and the launch method shows in one place how the child is
started.
source: default

## resources
Queues, notifiers, DVRs, files and user events are created in Pre Launch Init.
- What the helper loop uses (its user events, its queue) is released in `close` (`close-vi`).
- Everything else Pre Launch Init opened (DVRs, notifiers, files the loop does not use) is released in Stop Core.
- Release work lives in member VIs (`close`, or a release method per group of resources), not loose on an override's
  diagram, so the same VI serves Stop Core, `close` and a failed Pre Launch Init (`pli-failure-cleanup`). A release VI
  must accept a resource that was never created: its errors from an invalid reference end in Clear Errors.
- A Stop Core that would only call its parent is not created.
source: default

## stop-core-order
Stop Core calls its parent first, then releases. The parent Stop Core tells the auto-stop children to stop, so a child
is told to stop before the resources it may use are released.
Existing actors that release before Call Parent keep that order.
source: default

## pli-failure-cleanup
A Pre Launch Init that fails cleans up after itself, because Stop Core does not run after a failed Pre Launch Init
(`knowledge/actor-framework.md`). The creating and the cleanup live in ONE member VI, `createResources`
(`naming.role-names`): it creates every resource Pre Launch Init owns (calling `createEvents` and the like), merges
their errors, and a case structure on that merged error runs, in its Error case, the same release VIs that Stop Core
and `close` use (`resources`) on whatever was created. The No Error case does nothing. It returns the error. Pre Launch
Init calls only `createResources` (class and error), so a failure fails the launch.
Why: one release VI per resource group, reused, so a cleanup is written once and cannot drift between the paths; and
the whole member VI can be written and generated in one piece, with Pre Launch Init's diagram one call.
source: default

## events-typedef
An actor's own user events live in ONE typedef cluster, held in one private field, with ONE accessor pair for the
whole typedef, each accessor made only when used. `createEvents` creates every event, bundles them (Bundle By Name)
and does one `Write`. Every user (the loop, `stop`, `close`, senders) does one `Read` + Unbundle By Name. A new event
is one new element, not a new field. An actor with one event still uses the typedef. Notifiers and queues are not
user events, and this rule does not cover them.
source: default

## global-events
Events every actor may need (global stop, emergency stop, ...) live in their own typedef, never mixed into an
actor's own events typedef. The root creates them in its Pre Launch Init and passes them down before each launch,
inside the child's pre-launch settings (`prelaunch-settings`). A manager that launches its own children passes them on
the same way. The root destroys them in its own `close`, after its children have stopped.
source: default

## helper-loop-vi
A helper loop is a class member VI that Actor Core starts beside Call Parent. It talks to its own actor only
through `Read Self Enqueuer` and `Send` VIs, never by changing private data (it holds a copy of the object). It
lives in `Helpers` (`layout.class-folders`).
source: default

## helper-loop-error-case
The error case is INSIDE the loop. The registration refnum comes in from `init` and Unregister For Events sits after
the loop, outside the error case, and runs regardless of an incoming error (`registration`). The loop carries the error in a shift register; inside the loop, a case structure on
that error:
- **Error case:** the loop stops at this iteration and passes the error on; the registration refnum is wired
  through (`registration`).
- **No Error case:** the loop's work (the event structure, or the timed or polling work).
After the loop: Unregister → Merge Errors → `error out`.
Why: the registration always exists, so the stop always reaches the loop, and an error ends the loop on its next
iteration instead of leaving it waiting.
source: default

## registration
Each actor with a helper loop has a private, static `init` member that Actor Core calls in series BEFORE Call Parent
(class and error). `init` does what Actor Core sets up: Register For Events on a fresh "no error" (and, for an actor
that launches nested actors, those launches), with the registration refnum out on its pane. The loop VI takes the
refnum as an input: it enters the event structure's dynamic event terminal (left edge), the terminal's right-side
output is wired out of the loop into Unregister For Events, which sits right after the loop, outside the error case,
and runs regardless of an incoming error. In the Error case the refnum is wired straight through (case input tunnel
to case output tunnel), so the output tunnel carries the live refnum from every frame. Unregister takes the refnum
only from the loop's output tunnel, so it runs after the loop by data flow. There is no separate tunnel for the
refnum, and no wire around the event structure. New code never registers in Pre Launch Init.
Why: user events are not latched. With Register inside the loop VI, a Call Parent that returns at once (an error
wired into it, e.g. a failed nested launch) lets the stop hook generate the stop before the loop has registered; the
stop is lost, the loop never exits, `close` never runs, no Last Ack is sent and the tree hangs until LabVIEW
restarts. Measured in a harness run (2026-10): that failure hung the tree with Register in the loop VI, and passed
with `init` (Last Ack in 70 ms with the real error; early stop 5 of 5, no hang, on two actors). The refnum through
the Error case: with a use-default tunnel there, an Error-case exit hands Unregister a null refnum (1055, nothing
unregistered, and the Merge order hides the 1055); wired through, Unregister gets the live refnum. Unregister fed
straight from the refnum control runs as soon as the loop VI starts and unregisters before the loop waits: no stop
event arrives and every stop hangs the actor. Both measured in an evaluation, 2026-10.
Instead of: Register For Events inside the loop VI right before the loop; a use-default refnum tunnel in the Error
case; Unregister fed from the refnum control.
source: default

## stop-mechanism
Every helper-loop VI has at least one loop that waits on an asynchronous stop: a user event by default, or another
async mechanism (a notifier, a queue). Every loop stops the others when it ends, whatever ended it:
- The event loop exits on the stop and sets a local `stop` to T, which stops every other loop in the VI (polling,
  timed producer, ...).
- Every other loop, after it ends (on an error or on `stop`), calls the actor's own `stop` member in series (a Flat
  Sequence after the loop), then Clear Errors on that call: a second stop to a loop that has already ended does
  nothing (nobody is registered any more), and its error is ignored on purpose.
- A loop VI with only one loop: that loop is the event loop, and the stop event ends it. A local `stop` exists only
  when there is a second loop.
- All the loops sit in the one loop VI, because a local works only inside the VI that owns the control (Actor Core
  cannot write it). `stop` is written F before the loops start, because an off-pane control keeps its last value.
- Never stop a loop by aborting it.
Why: with the local written by the event loop only, a producer that ends on an error stops only itself; the event
loop waits for the stop event, which Actor Core sends only after Call Parent returns, which waits on the loop VI, so
the actor runs on with a dead producer until shutdown. Built and run in a harness run (2026-10), no hang.
source: default

## stop-site
Actor Core sends the stop right after Call Parent: it generates the stop event (the `stop` member). The local `stop`
is set inside the loop VI by its event loop (`stop-mechanism`); Actor Core cannot write it. The stop
hook runs on a fresh error chain. Call Parent's `error out` only sets the order, and nothing consumes it there. The
hook takes the class wire from before Call Parent (the child type).
Why: the stop is sent whenever Call Parent returns, for any reason; a Call Parent error cannot skip it.
source: default

## close-vi
The loop VI's `error out` and the stop hook's `error out` join in Merge Errors and feed `close`. `close` destroys the
user events and releases the loop's queue. Errors ignored on purpose inside it end in Clear Errors
(`errors.ignored-errors`). Actor Core returns the merged error, including Call Parent's. An error then ends the
actor (`errors.default-policy`) unless an error-handling plan says otherwise.
Why: `close` can run only after the loop has exited and the stop has been sent. Destroying earlier hangs the actor:
a Destroy in Stop Core runs inside Call Parent, before the stop, so the stop goes into a dead refnum
(`knowledge/actor-framework.md`).
Existing actors that generate and destroy in Stop Core keep that shape.
source: default

## timed-work
"Do X every N ms" is a second loop in the loop VI, timed by its own wait and stopped by the local `stop`
(`stop-mechanism`). An event structure's Timeout frame is used only when its meaning is the purpose: a check that
runs when no event has come for a while (an idle or watchdog check). Otherwise there is no Timeout frame, or an empty
one where the build tool needs it (`knowledge/labview-mcp.md`; LabVIEW itself needs one only when the Timeout
terminal is wired). Never use a 0 ms Timeout with non-blocking work (a busy loop).
source: default

## hook-vis
An override's work lives in hook VIs placed beside, before or after Call Parent, one job per hook. A hook takes the
class wire and the error. A hook on Handle Error may also take `stop actor?` in and out. A hook that needs another
override terminal (`Last Ack`, a This-VI reference) may take it.
source: default

## handle-error-order
Handle Error calls the parent first. The parent handles the normal stop and returns `stop actor?` = T. The actor's
own handler runs after it, on Call Parent's outputs, only where an error-handling plan exists
(`errors.plan-required`). It may overrule `stop actor?` only as the plan says. Without a plan, Handle Error is not
overridden (AF default: stop on error), or holds only the local log.
Existing actors with the handler before Call Parent keep it.
source: default

## handle-last-ack
Handle Last Ack Core is not overridden by default. The AF default passes a child's error to the caller's Handle Error,
which gives the fail-safe stop. Override it only for a relaunch plan, or when something must know that a child
stopped (e.g. a status table). The override calls its parent and keeps the parent's error.
source: default

## messages
Messages are generated by Message Maker, in the actor's `Messages` folder. A message carries references but does not
own them: the actor that created a reference closes it. Drop Message Core is overridden only for the rare message
that owns a reference.
source: default
