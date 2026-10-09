# Convention: errors
status: in force
written: (setup fills in the date)

> Default template. `conventions/setup.md` copies it into `<repo>/.labview/conventions/errors.md` and settles each
> rule. The rules here are the policy; where Handle Error sits relative to Call Parent is in
> `af-shapes.handle-error-order`.

## default-policy
Without an error-handling plan from the user, errors are fail-safe:
- An error stops the actor (AF's Handle Error: `stop actor?` = T).
- Every actor shuts down its children, through AF's default propagation.
- Shutdown puts hardware into a safe state, in `close` or Stop Core (e.g. a heater is switched off).
- The error is logged locally (`log-local`).
Why: doing nothing on an error is the dangerous option. If the temperature sensor fails while a heater is on,
shutting down and switching the heater off is the safe behaviour.
source: default

## plan-required
Reporting an error up, recovering (reconnect, retry) or keeping the actor running exists only where the user has
specified an error-handling plan. The plan is recorded in `decisions.md` and in the actor's description. Never add
recovery logic on your own.
source: default

## no-plan-statement
Where there is no plan, the actor says so explicitly. Its class description, and a comment on its Handle Error (if
there is one), carry: `no error-handling plan: stop on any error`.
source: default

## log-local
Errors are logged locally, to the project's own error log. The project names its log mechanism. In a new project,
ask once and record the answer here.
source: default

## loop-errors
On an error, a helper loop exits, logs the error, and stops its actor (`Send Normal Stop` to itself). The actor's
children stop with it. `close` and Stop Core then put hardware into a safe state. Without a plan, nothing else
happens.
source: default

## ignored-errors
An error output that is deliberately not handled is never left unwired. It ends in `Clear Errors.vi`, which marks
"not handled on purpose". Typical cases: a queue destroyed regardless, or a stop sent to an event nobody
registered. An unwired `error out` in new code is a defect.
source: default

## release-errors
Errors from release work in Stop Core (which has no error out to its caller) go to the local log, or end in Clear
Errors when they are ignored on purpose.
source: default
