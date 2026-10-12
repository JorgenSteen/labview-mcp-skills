# Convention: naming
status: in force
written: (setup fills in the date)

> Default template. `conventions/setup.md` copies it into `<repo>/.labview/conventions/naming.md` and settles each
> rule. An existing project's own naming convention always wins over this file.

## prefix
Every hand-written file starts with `<P>-<ABBR>-`. `<P>` is the project prefix (`project.json` `prefix`). `<ABBR>`
is the abbreviation of the owning actor, class or library, unique within the project. Example:
`PRJ-COM-helperCommunicationReceiver.vi`. A top-level VI with no owner (a launcher, a test runner) is
`<P>-<name>.vi`, e.g. `PRJ-launcher.vi`.
Why: a file name says who owns it, also outside LabVIEW (git, search, file lists).
source: default

## method-case
Class members are methods and are named in camelCase after the prefix. That covers every member VI, including
helper-loop VIs, hook VIs and custom accessors. Example: `<P>-<ABBR>-readSettings.vi`.
source: default

## function-case
Plain function VIs (not members of any class) are named in snake_case after the prefix. Example:
`<P>-<ABBR>-format_timestamp.vi`.
source: default

## typedef-case
Typedefs are named in UPPER_SNAKE after the prefix. Example: `<P>-<ABBR>-PRELAUNCH_SETTINGS.ctl`.
source: default

## override-names
AF overrides (`Pre Launch Init.vi`, `Actor Core.vi`, `Stop Core.vi`, `Handle Error.vi`, ...) and interface overrides keep
the parent's name. Message Maker products keep the tool's names (`<method> Msg.lvclass`, `Send <method>.vi`,
`Do.vi`).
source: default

## accessor-names
Generated accessors keep the default names `Read <field>` / `Write <field>`, with no rename. A custom accessor (a
grouping of fields that belong together) gets a proper camelCase name per `method-case`.
source: default

## class-library-names
Classes and libraries are named `<P>-<ABBR>-<name>`, with `<name>` in snake_case. Example:
`<P>-HWM-hardware_manager.lvclass`.
source: default

## field-names
Private data fields are named in camelCase without the prefix. Examples: `events`, `prelaunchSettings`.
source: default

## element-labels
Typedef element labels are camelCase. Where the labels are the keys of an external format (JSON, a file header), they
follow that format (e.g. snake_case keys).
source: default

## role-names
Members and typedefs with a fixed role in an actor (`af-shapes`) have these default names:

| Role | Default name |
|---|---|
| helper-loop VI | `<P>-<ABBR>-helper<Purpose>.vi`, e.g. `helperCommunicationReceiver` |
| creates everything Pre Launch Init owns, cleans up on its own error | `<P>-<ABBR>-createResources.vi` |
| creates the actor's user events (called by `createResources`) | `<P>-<ABBR>-createEvents.vi` |
| registers the helper loop's events before Call Parent, and launches a root's nested actors (Actor Core, `af-shapes.registration`) | `<P>-<ABBR>-init.vi` |
| sends the helper loop's stop (Actor Core) | `<P>-<ABBR>-stop.vi` |
| releases what the helper loop used (Actor Core) | `<P>-<ABBR>-close.vi` |
| the actor's own user events | `<P>-<ABBR>-EVENTS.ctl`, field `events` |
| global events (root) | `<P>-<ABBR>-GLOBAL_EVENTS.ctl`, `<ABBR>` = the root's |
| pre-launch settings | `<P>-<ABBR>-PRELAUNCH_SETTINGS.ctl`, field `prelaunchSettings` |
| writes the pre-launch settings (custom accessor) | `<P>-<ABBR>-writePrelaunchSettings.vi` |
| launches a child (a method of the caller) | `<P>-<ABBR>-launch<Child>.vi`, e.g. `<P>-ROOT-launchHwm.vi` |

An existing project's own role names (found by the analysis) replace these.
source: default
